import json
from typing import Optional
from ..config import settings, get_versioned_db_paths
from ..database.doc_repository import doc_repository
from ..database.models import DocChunk, SearchResult
import sqlite3
import sqlite_vec


class APISearchResult:
    def __init__(
        self,
        chunk_type: str,
        class_id: Optional[int],
        method_id: Optional[int],
        class_name: str,
        method_name: Optional[str],
        signature: Optional[str],
        javadoc: Optional[str],
        params: Optional[list],
        throws: Optional[list],
        return_type: Optional[str],
        score: float,
        source: str = "api_database",
    ):
        self.chunk_type = chunk_type
        self.class_id = class_id
        self.method_id = method_id
        self.class_name = class_name
        self.method_name = method_name
        self.signature = signature
        self.javadoc = javadoc
        self.params = params
        self.throws = throws
        self.return_type = return_type
        self.score = score
        self.source = source

    def to_dict(self):
        return {
            "type": self.chunk_type,
            "class_id": self.class_id,
            "method_id": self.method_id,
            "class": self.class_name,
            "method": self.method_name,
            "signature": self.signature,
            "javadoc": self.javadoc,
            "params": self.params,
            "throws": self.throws,
            "return_type": self.return_type,
            "score": round(self.score, 4),
            "source": self.source,
        }


class SearchService:
    _model = None

    @classmethod
    def get_embedding_model(cls):
        if cls._model is None:
            from sentence_transformers import SentenceTransformer

            cls._model = SentenceTransformer(settings.embedding_model)
        return cls._model

    def get_embedding(self, text: str) -> list[float]:
        model = self.get_embedding_model()
        embedding = model.encode(text, device="cpu")
        return embedding.tolist()

    def search_api(
        self, query: str, version: str, top_k: int = 5, chunk_type: Optional[str] = None
    ) -> list[APISearchResult]:
        query_vector = self.get_embedding(query)

        vec_db_path, main_db_path = get_versioned_db_paths(version)

        results = []
        search_vec = sqlite_vec.serialize_float32(query_vector)

        with sqlite3.connect(vec_db_path) as vec_conn:
            sqlite_vec.load(vec_conn)

            sql = """
                SELECT id, chunk_type, class_id, method_id, text, distance
                FROM api_chunks
                WHERE embedding MATCH ?
            """
            params = [search_vec]

            if chunk_type:
                sql = """
                    SELECT id, chunk_type, class_id, method_id, text, distance
                    FROM api_chunks
                    WHERE embedding MATCH ? AND chunk_type = ?
                """
                params = [search_vec, chunk_type]

            sql += " ORDER BY distance LIMIT ?"
            params.append(top_k * 3)

            cursor = vec_conn.execute(sql, params)
            rows = cursor.fetchall()

            for row in rows:
                chunk_id, chunk_type, class_id, method_id, text, distance = row

                if distance is None:
                    continue

                if version and chunk_type != "class" and chunk_type != "method":
                    continue

                result = self._build_api_result(
                    chunk_type=chunk_type,
                    class_id=class_id,
                    method_id=method_id,
                    score=1.0 - distance,
                    version=version,
                )
                if result and len(results) < top_k:
                    results.append(result)

        return results[:top_k]

    def _build_api_result(
        self, chunk_type: str, class_id: Optional[int], method_id: Optional[int], score: float, version: str
    ) -> Optional[APISearchResult]:
        main_db_path, _ = get_versioned_db_paths(version)

        with sqlite3.connect(main_db_path) as main_conn:
            main_conn.row_factory = sqlite3.Row

            if chunk_type == "class" and class_id:
                cursor = main_conn.execute("SELECT * FROM classes WHERE id = ?", (class_id,))
                row = cursor.fetchone()
                if row:
                    return APISearchResult(
                        chunk_type="class",
                        class_id=class_id,
                        method_id=None,
                        class_name=row["full_name"],
                        method_name=None,
                        signature=None,
                        javadoc=row["javadoc"],
                        params=None,
                        throws=None,
                        return_type=None,
                        score=score,
                    )

            elif chunk_type == "method" and method_id:
                cursor = main_conn.execute(
                    """
                    SELECT m.*, c.full_name as class_name
                    FROM methods m
                    JOIN classes c ON m.class_id = c.id
                    WHERE m.id = ?
                """,
                    (method_id,),
                )
                row = cursor.fetchone()
                if row:
                    params = json.loads(row["params"]) if row["params"] else []
                    throws = json.loads(row["throws"]) if row["throws"] else []

                    return APISearchResult(
                        chunk_type="method",
                        class_id=row["class_id"],
                        method_id=method_id,
                        class_name=row["class_name"],
                        method_name=row["name"],
                        signature=row["signature"],
                        javadoc=row["javadoc"],
                        params=params,
                        throws=throws,
                        return_type=row["return_type"],
                        score=score,
                    )

        return None

    def search(
        self, query: str, version: str, top_k: int = 5, doc_type: Optional[str] = None
    ) -> list[SearchResult]:
        query_vector = self.get_embedding(query)
        return doc_repository.search_chunks(
            version=version, query_vector=query_vector, top_k=top_k, doc_type=doc_type
        )

    def add_doc_chunk(
        self,
        version: str,
        doc_type: str,
        source_file: str,
        chunk_index: int,
        heading: Optional[str],
        content: str,
    ) -> int:
        chunk_vector = self.get_embedding(content)
        chunk = DocChunk(
            version=version,
            doc_type=doc_type,
            source_file=source_file,
            chunk_index=chunk_index,
            heading=heading,
            content=content,
            chunk_vector=chunk_vector,
        )
        return doc_repository.add_chunk(chunk)

    def add_doc_chunks_batch(self, chunks: list[dict]) -> int:
        total = 0
        for chunk_data in chunks:
            chunk = DocChunk(**chunk_data)
            if not chunk.chunk_vector:
                chunk.chunk_vector = self.get_embedding(chunk.content)
            doc_repository.add_chunk(chunk)
            total += 1
        return total

    def delete_version_chunks(self, version: str) -> int:
        return doc_repository.delete_chunks_by_version(version)


search_service = SearchService()
