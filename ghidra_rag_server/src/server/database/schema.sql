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

-- Package-Class relationship
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
-- Vector Search (sqlite-vec)
-- ============================================================

-- API向量表: 用于API语义搜索
CREATE VIRTUAL TABLE IF NOT EXISTS api_chunks USING vec0(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version TEXT NOT NULL,
    chunk_type TEXT NOT NULL,
    class_id INTEGER,
    method_id INTEGER,
    text TEXT NOT NULL,
    embedding FLOAT[384]
);

-- API向量表元数据
CREATE TABLE IF NOT EXISTS api_chunks_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version VARCHAR(20) NOT NULL,
    chunk_type VARCHAR(20) NOT NULL,
    class_id INTEGER,
    method_id INTEGER,
    text TEXT NOT NULL,
    FOREIGN KEY (class_id) REFERENCES classes(id),
    FOREIGN KEY (method_id) REFERENCES methods(id)
);

-- 文档向量表: 用于用户指南等文档语义搜索
CREATE VIRTUAL TABLE IF NOT EXISTS doc_chunks USING vec0(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version TEXT NOT NULL,
    doc_type TEXT NOT NULL,
    source_file TEXT NOT NULL,
    chunk_index INTEGER DEFAULT 0,
    heading TEXT,
    content TEXT NOT NULL,
    embedding FLOAT[384]
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
CREATE INDEX IF NOT EXISTS idx_chunks_version ON doc_chunks(version);
CREATE INDEX IF NOT EXISTS idx_chunks_doc_type ON doc_chunks(doc_type);
CREATE INDEX IF NOT EXISTS idx_api_chunks_class ON api_chunks_metadata(class_id);
CREATE INDEX IF NOT EXISTS idx_api_chunks_method ON api_chunks_metadata(method_id);
CREATE INDEX IF NOT EXISTS idx_api_chunks_type ON api_chunks_metadata(chunk_type);
CREATE INDEX IF NOT EXISTS idx_api_chunks_version ON api_chunks_metadata(version);
