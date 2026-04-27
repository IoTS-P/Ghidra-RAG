import json
from typing import Optional
from .connection import get_db
from .models import DocChunk, SearchResult


class DocRepository:
    def __init__(self, version: Optional[str] = None):
        self.version = version
        self.db = get_db(version)

    def add_chunk(self, chunk: DocChunk) -> int:
        with self.db.get_vec_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO doc_chunks 
                (version, doc_type, source_file, chunk_index, heading, content, chunk_vector)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    chunk.version,
                    chunk.doc_type,
                    chunk.source_file,
                    chunk.chunk_index,
                    chunk.heading,
                    chunk.content,
                    json.dumps(chunk.chunk_vector) if chunk.chunk_vector else None,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def search_chunks(
        self,
        version: str,
        query_vector: list[float],
        top_k: int = 5,
        doc_type: Optional[str] = None,
    ) -> list[SearchResult]:
        import sqlite_vec

        with self.db.get_vec_connection() as conn:
            cursor = conn.cursor()
            search_vec = sqlite_vec.serialize_float32(query_vector)

            sql = """
                SELECT id, doc_type, source_file, heading, content, distance
                FROM doc_chunks
                WHERE embedding MATCH ? AND version = ?
            """
            params = [search_vec, version]

            if doc_type:
                sql = """
                    SELECT id, doc_type, source_file, heading, content, distance
                    FROM doc_chunks
                    WHERE embedding MATCH ? AND version = ? AND doc_type = ?
                """
                params = [search_vec, version, doc_type]

            sql += " ORDER BY distance LIMIT ?"
            params.append(top_k)

            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()

            results = []
            for row in rows:
                chunk_id, doc_type, source_file, heading, content, distance = row
                score = 1.0 - distance if distance is not None else 0.0
                results.append(
                    SearchResult(
                        chunk_id=chunk_id,
                        content=content,
                        heading=heading,
                        source_file=source_file,
                        score=score,
                        doc_type=doc_type,
                    )
                )
            return results

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        return dot_product / (magnitude1 * magnitude2)

    def get_chunks_by_source(self, version: str, source_file: str) -> list[DocChunk]:
        with self.db.get_vec_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM doc_chunks WHERE version = ? AND source_file = ?",
                (version, source_file),
            )
            rows = cursor.fetchall()
            chunks = []
            for row in rows:
                c = dict(row)
                if c.get("chunk_vector"):
                    c["chunk_vector"] = json.loads(c["chunk_vector"])
                chunks.append(DocChunk(**c))
            return chunks

    def delete_chunks_by_version(self, version: str) -> int:
        with self.db.get_vec_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM doc_chunks WHERE version = ?", (version,))
            conn.commit()
            return cursor.rowcount


doc_repository = DocRepository()
