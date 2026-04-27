#!/usr/bin/env python3
"""
Ingest documentation chunks for semantic search.

This script parses Ghidra documentation (HTML/MD files), splits them into
chunks by heading, generates vector embeddings, and stores them in the
doc_chunks virtual table for semantic search.
"""

import json
import re
import sys
from pathlib import Path
from tqdm import tqdm
import sqlite3

sys.path.insert(0, str(Path(__file__).parent.parent / "ghidra_rag_server" / "src"))

from bs4 import BeautifulSoup
import sqlite_vec

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


def get_db_paths(version: str):
    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / "data" / version
    data_dir.mkdir(exist_ok=True)
    return {"main": data_dir / "ghidra_rag.db", "vec": data_dir / "ghidra_vec.db"}


def init_doc_chunks(vec_db_path: Path):
    conn = sqlite3.connect(vec_db_path)
    sqlite_vec.load(conn)

    conn.execute("DROP TABLE IF EXISTS doc_chunks")

    conn.execute("""
        CREATE VIRTUAL TABLE doc_chunks USING vec0(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version TEXT NOT NULL,
            doc_type TEXT NOT NULL,
            source_file TEXT NOT NULL,
            chunk_index INTEGER DEFAULT 0,
            heading TEXT,
            content TEXT NOT NULL,
            embedding FLOAT[384]
        )
    """)

    conn.commit()
    return conn


def split_html_chunks(soup: BeautifulSoup, source_file: str) -> list[dict]:
    chunks = []
    current_heading = "Untitled"
    current_content = []

    for tag in soup.find_all(["h1", "h2", "h3", "p", "ul", "ol", "pre", "code"]):
        if tag.name in ["h1", "h2", "h3"]:
            if current_content:
                text = clean_text("\n".join(current_content))
                if text.strip():
                    chunks.append(
                        {
                            "heading": current_heading,
                            "content": text,
                            "source_file": source_file,
                        }
                    )
                current_content = []

            heading_text = tag.get_text(strip=True)
            if heading_text:
                current_heading = heading_text

        elif tag.name in ["p", "li"]:
            text = tag.get_text(strip=True)
            if text:
                current_content.append(text)

        elif tag.name in ["pre", "code"]:
            text = tag.get_text(strip=True)
            if text and len(text) > 10:
                current_content.append(f"```\n{text}\n```")

    if current_content:
        text = clean_text("\n".join(current_content))
        if text.strip():
            chunks.append(
                {
                    "heading": current_heading,
                    "content": text,
                    "source_file": source_file,
                }
            )

    return chunks


def split_md_chunks(content: str, source_file: str) -> list[dict]:
    chunks = []
    current_heading = "Untitled"
    current_content = []
    in_code_block = False
    code_block_content = []

    lines = content.split("\n")

    for line in lines:
        if line.startswith("```"):
            if not in_code_block:
                in_code_block = True
                code_block_content = []
            else:
                code = "\n".join(code_block_content)
                if len(code) > 10:
                    current_content.append(f"```\n{code}\n```")
                in_code_block = False
                code_block_content = []
            continue

        if in_code_block:
            code_block_content.append(line)
            continue

        if line.startswith("#"):
            if current_content:
                text = clean_text("\n".join(current_content))
                if text.strip():
                    chunks.append(
                        {
                            "heading": current_heading,
                            "content": text,
                            "source_file": source_file,
                        }
                    )
                current_content = []

            heading = line.lstrip("#").strip()
            if heading:
                current_heading = heading
            continue

        stripped = line.strip()
        if stripped:
            current_content.append(stripped)

    if current_content:
        text = clean_text("\n".join(current_content))
        if text.strip():
            chunks.append(
                {
                    "heading": current_heading,
                    "content": text,
                    "source_file": source_file,
                }
            )

    return chunks


def clean_text(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def build_doc_text(heading: str, content: str, doc_type: str) -> str:
    parts = [f"Document: {heading}", f"Type: {doc_type}", "", content]
    return "\n".join(parts)


def get_doc_type(source_file: str) -> str:
    name = Path(source_file).stem.lower()
    if "install" in name:
        return "installation"
    if "change" in name or "history" in name:
        return "changelog"
    if "whats" in name or "new" in name:
        return "release_notes"
    if "cheat" in name:
        return "cheatsheet"
    if "user" in name or "guide" in name:
        return "user_guide"
    if "class" in name or "coding" in name:
        return "guide"
    if "filesystem" in name:
        return "guide"
    return "documentation"


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Ingest Ghidra documentation for semantic search")
    parser.add_argument("--version", default="11.3.2", help="Ghidra version")
    args = parser.parse_args()

    version = args.version
    base_dir = Path(__file__).parent.parent
    docs_dir = base_dir / "docs"
    db_paths = get_db_paths(version)
    vec_db_path = db_paths["vec"]

    version_path = docs_dir / version

    if not version_path.exists():
        print(f"Error: Version {version} not found in {docs_dir}")
        sys.exit(1)

    print(f"Processing documentation for version: {version}")
    print(f"Output: {vec_db_path}")

    vec_conn = init_doc_chunks(vec_db_path)
    sqlite_vec.load(vec_conn)

    from sentence_transformers import SentenceTransformer

    print(f"\nLoading embedding model: {EMBEDDING_MODEL}")
    model = SentenceTransformer(EMBEDDING_MODEL, device="cpu")

    all_chunks = []

    html_files = list(version_path.glob("**/*.html"))
    md_files = list(version_path.glob("**/*.md"))
    html_files = [f for f in html_files if "ghidra_stubs" not in str(f) and "/api/" not in str(f)]
    md_files = [f for f in md_files if "/api/" not in str(f)]

    print(f"\nFound {len(html_files)} HTML files, {len(md_files)} MD files")

    for html_file in tqdm(html_files, desc="Processing HTML files"):
        try:
            content = html_file.read_text(encoding="utf-8", errors="ignore")
            soup = BeautifulSoup(content, "html.parser")

            doc_type = get_doc_type(str(html_file))
            chunks = split_html_chunks(soup, str(html_file.relative_to(base_dir)))

            for i, chunk in enumerate(chunks):
                text = build_doc_text(chunk["heading"], chunk["content"], doc_type)
                all_chunks.append(
                    {
                        "version": version,
                        "doc_type": doc_type,
                        "source_file": chunk["source_file"],
                        "chunk_index": i,
                        "heading": chunk["heading"],
                        "content": text,
                    }
                )
        except Exception as e:
            print(f"\nWarning: Failed to process {html_file}: {e}")

    for md_file in tqdm(md_files, desc="Processing MD files"):
        try:
            content = md_file.read_text(encoding="utf-8", errors="ignore")

            doc_type = get_doc_type(str(md_file))
            chunks = split_md_chunks(content, str(md_file.relative_to(base_dir)))

            for i, chunk in enumerate(chunks):
                text = build_doc_text(chunk["heading"], chunk["content"], doc_type)
                all_chunks.append(
                    {
                        "version": version,
                        "doc_type": doc_type,
                        "source_file": "docs/" + str(md_file.relative_to(version_path)),
                        "chunk_index": i,
                        "heading": chunk["heading"],
                        "content": text,
                    }
                )
        except Exception as e:
            print(f"\nWarning: Failed to process {md_file}: {e}")

    print(f"\nTotal chunks: {len(all_chunks)}")

    texts = [c["content"] for c in all_chunks]

    print(f"\nGenerating embeddings for {len(texts)} chunks...")
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=64)

    print("\nStoring chunks in database...")
    for i, (chunk, embedding) in enumerate(tqdm(list(zip(all_chunks, embeddings)), desc="Storing")):
        vec_bytes = sqlite_vec.serialize_float32(embedding.tolist())
        vec_conn.execute(
            """
            INSERT INTO doc_chunks (version, doc_type, source_file, chunk_index, heading, content, embedding)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chunk["version"],
                chunk["doc_type"],
                chunk["source_file"],
                chunk["chunk_index"],
                chunk["heading"],
                chunk["content"],
                vec_bytes,
            ),
        )

    vec_conn.commit()
    vec_conn.close()

    print("\n" + "=" * 60)
    print("Document Ingestion Complete!")
    print(f"Total chunks: {len(all_chunks)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
