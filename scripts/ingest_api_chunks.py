#!/usr/bin/env python3
"""
Ingest API chunks for semantic search.

This script creates vector embeddings for classes and methods from the existing
API database, enabling semantic search that returns structured API entries.
"""

import json
import sys
from pathlib import Path
from tqdm import tqdm
import sqlite3

sys.path.insert(0, str(Path(__file__).parent.parent / "ghidra_rag_server" / "src"))

from sentence_transformers import SentenceTransformer
import sqlite_vec


EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


def get_db_paths(version: str):
    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / "data" / version
    data_dir.mkdir(exist_ok=True)
    return {"main": data_dir / "ghidra_rag.db", "vec": data_dir / "ghidra_vec.db"}


def init_vec_db(vec_db_path: Path):
    conn = sqlite3.connect(vec_db_path)
    sqlite_vec.load(conn)

    conn.execute("DROP TABLE IF EXISTS api_chunks")
    conn.execute("DROP TABLE IF EXISTS api_chunks_metadata")

    conn.execute("""
        CREATE VIRTUAL TABLE api_chunks USING vec0(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version TEXT NOT NULL,
            chunk_type TEXT NOT NULL,
            class_id INTEGER,
            method_id INTEGER,
            text TEXT NOT NULL,
            embedding FLOAT[384]
        )
    """)

    conn.execute("""
        CREATE TABLE api_chunks_metadata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version VARCHAR(20) NOT NULL,
            chunk_type VARCHAR(20) NOT NULL,
            class_id INTEGER,
            method_id INTEGER,
            text TEXT NOT NULL
        )
    """)

    conn.commit()
    return conn


def build_class_text(class_data: dict, package_name: str = "") -> str:
    parts = [
        f"Class: {class_data['name']}",
        f"Package: {package_name}" if package_name else "Package: (none)",
    ]

    if class_data.get("extends"):
        parts.append(f"Extends: {class_data['extends']}")

    if class_data.get("implements"):
        parts.append(f"Implements: {class_data['implements']}")

    if class_data.get("javadoc"):
        parts.append(f"Description: {class_data['javadoc']}")

    if class_data.get("fields_summary"):
        parts.append(f"Fields: {class_data['fields_summary']}")

    return "\n".join(parts)


def build_method_text(method_data: dict, class_name: str = "") -> str:
    parts = [
        f"Method: {method_data['name']}",
        f"Class: {class_name}" if class_name else "",
        f"Signature: {method_data['signature']}",
    ]

    if method_data.get("javadoc"):
        parts.append(f"Description: {method_data['javadoc']}")

    if method_data.get("params"):
        params_str = ", ".join([f"{p['type_short']} {p['name']}" for p in method_data["params"]])
        parts.append(f"Parameters: {params_str if params_str else '(none)'}")

    if method_data.get("return_type"):
        return_desc = method_data.get("return_javadoc", "")
        parts.append(
            f"Returns: {method_data['return_type']} - {return_desc}"
            if return_desc
            else f"Returns: {method_data['return_type']}"
        )

    if method_data.get("throws"):
        throws_str = ", ".join(method_data["throws"])
        parts.append(f"Throws: {throws_str}")

    return "\n".join(parts)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Ingest Ghidra API chunks for semantic search")
    parser.add_argument("--version", required=True, help="Ghidra version")
    args = parser.parse_args()

    version = args.version

    print("=" * 60)
    print("Ghidra RAG - API Chunks Ingestion")
    print("=" * 60)

    db_paths = get_db_paths(version)
    print(f"\nMain DB: {db_paths['main']}")
    print(f"Vector DB: {db_paths['vec']}")

    if not db_paths["main"].exists():
        print("Error: Main database not found. Run ingest_api.py first.")
        sys.exit(1)

    vec_conn = init_vec_db(db_paths["vec"])
    sqlite_vec.load(vec_conn)

    print(f"\nLoading embedding model: {EMBEDDING_MODEL}")
    model = SentenceTransformer(EMBEDDING_MODEL)
    print(f"Embedding dimension: {EMBEDDING_DIM}")

    main_conn = sqlite3.connect(db_paths["main"])
    main_conn.row_factory = sqlite3.Row

    print(f"Processing version: {version}")

    print("\n" + "-" * 60)
    print("Processing Classes...")
    print("-" * 60)

    cursor.execute(
        """
        SELECT c.id, c.name, c.full_name, c.extends, c.implements, c.javadoc,
               p.name as package_name
        FROM classes c
        LEFT JOIN packages p ON c.package_id = p.id
        WHERE c.version = ?
        ORDER BY c.id
    """,
        (version,),
    )

    classes = cursor.fetchall()
    print(f"Found {len(classes)} classes")

    class_texts = []
    class_metadata = []

    for cls in tqdm(classes, desc="Building class texts"):
        row = dict(cls)
        javadoc = row.get("javadoc") or row.get("javdoc", "")

        cursor.execute(
            """
            SELECT name, field_type FROM fields 
            WHERE class_id = ? AND is_static = 0
            LIMIT 10
        """,
            (row["id"],),
        )
        fields = cursor.fetchall()
        fields_summary = (
            ", ".join([f"{f['field_type']} {f['name']}" for f in fields]) if fields else "(none)"
        )

        class_data = {
            "name": row["full_name"],
            "extends": row["extends"],
            "implements": row["implements"],
            "javadoc": javadoc,
            "fields_summary": fields_summary,
        }

        text = build_class_text(class_data, row.get("package_name", ""))
        class_texts.append(text)
        class_metadata.append(
            {"chunk_type": "class", "class_id": row["id"], "method_id": None, "text": text}
        )

    print(f"\nGenerating embeddings for {len(class_texts)} classes...")
    class_embeddings = model.encode(class_texts, show_progress_bar=True)

    print("Storing class chunks...")
    for i, (meta, embedding) in enumerate(zip(class_metadata, class_embeddings)):
        vec_bytes = sqlite_vec.serialize_float32(embedding.tolist())
        vec_conn.execute(
            """
            INSERT INTO api_chunks (version, chunk_type, class_id, method_id, text, embedding)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                version,
                meta["chunk_type"],
                meta["class_id"],
                meta["method_id"] or 0,
                meta["text"],
                vec_bytes,
            ),
        )

        vec_conn.execute(
            """
            INSERT INTO api_chunks_metadata (version, chunk_type, class_id, method_id, text)
            VALUES (?, ?, ?, ?, ?)
        """,
            (version, meta["chunk_type"], meta["class_id"], meta["method_id"], meta["text"]),
        )

    vec_conn.commit()
    print(f"Stored {len(class_texts)} class chunks")

    print("\n" + "-" * 60)
    print("Processing Methods...")
    print("-" * 60)

    cursor.execute(
        """
        SELECT m.id, m.class_id, m.name, m.signature, m.return_type, 
               m.return_javadoc, m.params, m.throws, m.javadoc,
               c.full_name as class_full_name
        FROM methods m
        JOIN classes c ON m.class_id = c.id
        WHERE c.version = ?
        ORDER BY m.id
    """,
        (version,),
    )

    methods = cursor.fetchall()
    print(f"Found {len(methods)} methods")

    method_texts = []
    method_metadata = []

    for method in tqdm(methods, desc="Building method texts"):
        row = dict(method)
        params = json.loads(row["params"]) if row["params"] else []
        throws = json.loads(row["throws"]) if row["throws"] else []

        method_data = {
            "name": row["name"],
            "signature": row["signature"],
            "return_type": row["return_type"],
            "return_javadoc": row["return_javadoc"],
            "params": params,
            "throws": throws,
            "javadoc": row["javadoc"],
        }

        text = build_method_text(method_data, row["class_full_name"])
        method_texts.append(text)
        method_metadata.append(
            {
                "chunk_type": "method",
                "class_id": row["class_id"],
                "method_id": row["id"],
                "text": text,
            }
        )

    print(f"\nGenerating embeddings for {len(method_texts)} methods...")
    method_embeddings = model.encode(method_texts, show_progress_bar=True)

    print("Storing method chunks...")
    for i, (meta, embedding) in enumerate(zip(method_metadata, method_embeddings)):
        vec_bytes = sqlite_vec.serialize_float32(embedding.tolist())
        chunk_id = len(class_texts) + i + 1
        vec_conn.execute(
            """
            INSERT INTO api_chunks (version, chunk_type, class_id, method_id, text, embedding)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                version,
                meta["chunk_type"],
                meta["class_id"],
                meta["method_id"] or 0,
                meta["text"],
                vec_bytes,
            ),
        )

        vec_conn.execute(
            """
            INSERT INTO api_chunks_metadata (version, chunk_type, class_id, method_id, text)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                version,
                meta["chunk_type"],
                meta["class_id"],
                meta["method_id"],
                meta["text"],
            ),
        )

    vec_conn.commit()
    print(f"Stored {len(method_texts)} method chunks")

    main_conn.close()
    vec_conn.close()

    print("\n" + "=" * 60)
    print("Ingestion Complete!")
    print(f"Total chunks: {len(class_texts) + len(method_texts)}")
    print(f"  - Classes: {len(class_texts)}")
    print(f"  - Methods: {len(method_texts)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
