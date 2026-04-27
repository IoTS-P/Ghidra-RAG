#!/usr/bin/env python3
import sqlite3
from pathlib import Path

SCHEMA_SQL = """
-- Ghidra RAG Database Schema
-- SQLite + sqlite-vec

-- ============================================================
-- Version Management
-- ============================================================

CREATE TABLE IF NOT EXISTS ghidra_versions (
    version VARCHAR(20) PRIMARY KEY,
    docs_path TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS db_version (
    db_version VARCHAR(20) PRIMARY KEY,
    ghidra_version VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    checksum TEXT
);

-- ============================================================
-- Package/Class/Method/Field Structure
-- ============================================================

CREATE TABLE IF NOT EXISTS packages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version VARCHAR(20) NOT NULL,
    name VARCHAR(255) NOT NULL,
    package_path TEXT NOT NULL,
    FOREIGN KEY (version) REFERENCES ghidra_versions(version)
);

CREATE TABLE IF NOT EXISTS classes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version VARCHAR(20) NOT NULL,
    name VARCHAR(255) NOT NULL,
    full_name VARCHAR(512) NOT NULL,
    package_id INTEGER REFERENCES packages(id),
    extends VARCHAR(512),
    implements TEXT,
    javadoc TEXT,
    html_file TEXT,
    json_file TEXT,
    has_examples BOOLEAN DEFAULT 0,
    FOREIGN KEY (version) REFERENCES ghidra_versions(version)
);

CREATE TABLE IF NOT EXISTS methods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id INTEGER REFERENCES classes(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    signature TEXT NOT NULL,
    return_type VARCHAR(255),
    return_javadoc TEXT,
    is_static BOOLEAN DEFAULT 0,
    is_constructor BOOLEAN DEFAULT 0,
    params TEXT,
    throws TEXT,
    javadoc TEXT,
    has_examples BOOLEAN DEFAULT 0
);

CREATE TABLE IF NOT EXISTS fields (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id INTEGER REFERENCES classes(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    field_type VARCHAR(255),
    is_static BOOLEAN DEFAULT 0,
    is_final BOOLEAN DEFAULT 0,
    constant_value TEXT,
    javadoc TEXT
);

CREATE TABLE IF NOT EXISTS package_class_relations (
    package_id INTEGER REFERENCES packages(id) ON DELETE CASCADE,
    class_id INTEGER REFERENCES classes(id) ON DELETE CASCADE,
    PRIMARY KEY (package_id, class_id)
);

-- ============================================================
-- Method Examples (Learning from LLM)
-- ============================================================

CREATE TABLE IF NOT EXISTS method_examples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    method_id INTEGER REFERENCES methods(id) ON DELETE CASCADE,
    example_code TEXT NOT NULL,
    description TEXT,
    scenario TEXT,
    expected_output TEXT,
    author VARCHAR(100),
    model_id VARCHAR(100),
    confidence FLOAT DEFAULT 0.5,
    status VARCHAR(20) DEFAULT 'pending',
    upvotes INTEGER DEFAULT 0,
    downvotes INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- Indexes
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_packages_version ON packages(version);
CREATE INDEX IF NOT EXISTS idx_packages_name ON packages(name);
CREATE INDEX IF NOT EXISTS idx_classes_version ON classes(version);
CREATE INDEX IF NOT EXISTS idx_classes_full_name ON classes(full_name);
CREATE INDEX IF NOT EXISTS idx_classes_package ON classes(package_id);
CREATE INDEX IF NOT EXISTS idx_methods_class ON methods(class_id);
CREATE INDEX IF NOT EXISTS idx_methods_name ON methods(name);
CREATE INDEX IF NOT EXISTS idx_fields_class ON fields(class_id);
CREATE INDEX IF NOT EXISTS idx_examples_method ON method_examples(method_id);
CREATE INDEX IF NOT EXISTS idx_examples_status ON method_examples(status);
"""


def init_database():
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)

    db_path = data_dir / "ghidra_rag.db"
    print(f"Creating database at: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA_SQL)
    conn.close()

    print(f"\nTables created:")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()
    for table in tables:
        print(f"  - {table[0]}")
    conn.close()

    print("\nDatabase initialization successful!")
    return db_path


if __name__ == "__main__":
    init_database()
