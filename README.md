# Ghidra RAG

[中文](./README_zh.md)

A normalized RAG (Retrieval-Augmented Generation) system for Ghidra API documentation.

## Features

- **Multi-version Support**: Manage documentation databases for different Ghidra versions (e.g., 11.3.2, 11.4.1)
- **Semantic Search**: Vector-based similarity search using sentence-transformers
- **Structured API Queries**: Browse classes, methods, fields, and package hierarchies
- **Method Examples**: Store and retrieve usage examples for API methods
- **RESTful API**: FastAPI-based server with comprehensive endpoints

## Architecture

```
ghidra_rag/
├── docs/                    # Ghidra documentation (HTML/MD)
│   └── {version}/           # Version-specific docs
├── data/                    # SQLite databases (versioned)
│   └── {version}/
│       ├── ghidra_rag.db    # Main database (packages, classes, methods)
│       └── ghidra_vec.db    # Vector database (embeddings)
├── scripts/                 # Ingestion scripts
│   ├── init_db.py           # Initialize database schema
│   ├── ingest_docs.py       # Ingest user documentation
│   ├── ingest_api.py        # Parse and ingest API JSON
│   └── ingest_api_chunks.py # Create API embeddings
├── ghidra_rag_server/        # FastAPI server
│   ├── src/server/
│   │   ├── routers/         # API endpoints
│   │   ├── services/        # Business logic
│   │   └── database/        # Database access
│   ├── Dockerfile
│   └── docker-compose.yml
└── ghidra_rag_client/        # Python client library
```

## Installation

### Prerequisites

- Python 3.10+
- pip

### Install from source

```bash
pip install -e ".[all]"
```

### Docker Setup

```bash
cd ghidra_rag_server
docker-compose up -d
```

## Database Structure

Each version has its own database pair in `data/{version}/`:

| Database | Purpose |
|----------|---------|
| `ghidra_rag.db` | Relational data: packages, classes, methods, fields, examples |
| `ghidra_vec.db` | Vector embeddings for semantic search |

## Usage

### 1. Initialize Database

```bash
# Create database for specific version
python scripts/init_db.py --version 11.3.2
```

### 2. Ingest Documentation

```bash
# Ingest user documentation (HTML/MD)
python scripts/ingest_docs.py --version 11.3.2

# Ingest API data from JSON files
python scripts/ingest_api.py --version 11.3.2 --docs-path ./docs

# Create vector embeddings for API
python scripts/ingest_api_chunks.py --version 11.3.2
```

### 3. Start Server

```bash
# Development
cd ghidra_rag_server
uvicorn src.server.main:app --reload

# Production (Docker)
cd ghidra_rag_server
docker-compose up -d
```

### 4. Auto-download Ghidra Documentation

Automatically download Ghidra releases and build databases:

```bash
# CLI
python scripts/download_ghidra.py list                    # List available versions
python scripts/download_ghidra.py download 11.3.2        # Download and process version

# Or via API
GET /api/v1/download/versions     # Get available versions
POST /api/v1/download            # Start download task (body: {"version": "11.3.2"})
GET /api/v1/download/status/{id} # Check download status
```

After download, docs are saved to `docs/{version}/` and databases to `data/{version}/`.

### 4. Using the Client

```python
from ghidra_rag_client import GhidraRAGClient

with GhidraRAGClient(base_url="http://localhost:8000") as client:
    # Search documentation
    results = client.search.search("how to analyze binary files")

    # Query API
    methods = client.api.get_methods("ghidra.app.script", version="11.3.2")
    hierarchy = client.api.get_hierarchy("ghidra.program.model.listing.CodeUnit")

    # Add method example
    client.api.add_method_example(
        class_name="ghidra.app.script.Script",
        method_name="println",
        example_code='println("Hello World")',
        description="Prints a message to the console"
    )
```

## API Endpoints

### Documentation Search

- `GET /api/v1/search?q=<query>&top_k=<n>&version=<v>` - Semantic search
- `POST /api/v1/search` - Search with request body

### API Queries

- `GET /api/class/{class_name}/methods` - Get class methods
- `GET /api/class/{class_name}/fields` - Get class fields
- `GET /api/class/{class_name}/hierarchy` - Get class hierarchy
- `GET /api/package/{package_name}/classes` - Get classes in package
- `GET /api/method/{class_name}/{method_name}` - Get method details
- `GET /api/method/{class_name}/{method_name}/examples` - Get method examples
- `POST /api/method/{class_name}/{method_name}/examples` - Add method example
- `POST /api/examples/{id}/vote` - Vote on example
- `PATCH /api/examples/{id}/status` - Update example status

### Version Management

- `GET /api/v1/versions` - List available versions
- `GET /api/v1/versions/default` - Get default version

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GHIDRA_RAG_DATA_DIR` | `./data` | Database directory |
| `GHIDRA_RAG_DEFAULT_VERSION` | `11.3.2` | Default Ghidra version |
| `GHIDRA_RAG_HOST` | `0.0.0.0` | Server host |
| `GHIDRA_RAG_PORT` | `8000` | Server port |

## Skills for LLM Agents

This project includes a skill definition for LLM agents (like OpenCode, Cursor, etc.) to use this RAG system.

### Skill Location

```
skills/ghidra_rag/
├── SKILL.md      # Skill definition for LLM agents
└── config.json   # RAG server configuration
```

### Supported Platforms

Copy the `skills/ghidra_rag/` directory to your LLM platform's skills directory:

- **OpenCode**: `~/.opencode/skills/` or `.opencode/skills/`
- **Cursor**: `.cursor/skills/`
- **Other**: Follow your platform's skill loading conventions

### Usage

When using the skill, the LLM agent can:

1. Read `config.json` to get the RAG server address
2. Query available Ghidra versions via `/api/v1/versions`
3. Perform semantic search on API and documentation
4. Query class hierarchies, methods, and fields

See `skills/ghidra_rag/SKILL.md` for the complete skill specification.

## License

MIT