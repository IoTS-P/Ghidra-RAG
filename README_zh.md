# Ghidra RAG

Ghidra 文档的 RAG（检索增强生成）系统，为 Ghidra API 文档提供语义搜索能力，支持多版本管理。

## 功能特性

- **多版本支持**：管理不同 Ghidra 版本（如 11.3.2、11.4.1）的文档数据库
- **语义搜索**：基于 sentence-transformers 的向量相似度搜索
- **结构化 API 查询**：浏览类、方法、字段和包层次结构
- **方法示例**：存储和检索 API 方法的使用示例
- **RESTful API**：基于 FastAPI 的服务器，提供完整的 API 端点

## 项目结构

```
ghidra_rag/
├── docs/                    # Ghidra 文档 (HTML/MD)
│   └── {version}/           # 按版本组织的文档
├── data/                    # SQLite 数据库（按版本区分）
│   └── {version}/
│       ├── ghidra_rag.db    # 主数据库（包、类、方法）
│       └── ghidra_vec.db    # 向量数据库（嵌入向量）
├── scripts/                 # 数据导入脚本
│   ├── init_db.py           # 初始化数据库结构
│   ├── ingest_docs.py       # 导入用户文档
│   ├── ingest_api.py        # 解析并导入 API JSON
│   └── ingest_api_chunks.py # 创建 API 嵌入向量
├── ghidra_rag_server/        # FastAPI 服务器
│   ├── src/server/
│   │   ├── routers/         # API 路由
│   │   ├── services/       # 业务逻辑
│   │   └── database/        # 数据库访问层
│   ├── Dockerfile
│   └── docker-compose.yml
└── ghidra_rag_client/        # Python 客户端库
```

## 安装

### 前置要求

- Python 3.10+
- pip

### 从源码安装

```bash
pip install -e ".[all]"
```

### Docker 部署

```bash
cd ghidra_rag_server
docker-compose up -d
```

## 数据库结构

每个版本在 `data/{version}/` 下有自己的数据库对：

| 数据库 | 用途 |
|--------|------|
| `ghidra_rag.db` | 关系数据：包、类、方法、字段、示例 |
| `ghidra_vec.db` | 用于语义搜索的向量嵌入 |

## 使用方法

### 1. 初始化数据库

```bash
# 为特定版本创建数据库
python scripts/init_db.py --version 11.3.2
```

### 2. 导入文档

```bash
# 导入用户文档 (HTML/MD)
python scripts/ingest_docs.py --version 11.3.2

# 从 JSON 文件导入 API 数据
python scripts/ingest_api.py --version 11.3.2 --docs-path ./docs

# 为 API 创建向量嵌入
python scripts/ingest_api_chunks.py --version 11.3.2
```

### 3. 启动服务器

```bash
# 开发模式
cd ghidra_rag_server
uvicorn src.server.main:app --reload

# 生产环境 (Docker)
cd ghidra_rag_server
docker-compose up -d
```

### 4. 使用客户端

```python
from ghidra_rag_client import GhidraRAGClient

with GhidraRAGClient(base_url="http://localhost:8000") as client:
    # 搜索文档
    results = client.search.search("how to analyze binary files")

    # 查询 API
    methods = client.api.get_methods("ghidra.app.script", version="11.3.2")
    hierarchy = client.api.get_hierarchy("ghidra.program.model.listing.CodeUnit")

    # 添加方法示例
    client.api.add_method_example(
        class_name="ghidra.app.script.Script",
        method_name="println",
        example_code='println("Hello World")',
        description="Prints a message to the console"
    )
```

## API 端点

### 文档搜索

- `GET /api/v1/search?q=<query>&top_k=<n>&version=<v>` - 语义搜索
- `POST /api/v1/search` - 通过请求体搜索

### API 查询

- `GET /api/class/{class_name}/methods` - 获取类的所有方法
- `GET /api/class/{class_name}/fields` - 获取类的所有字段
- `GET /api/class/{class_name}/hierarchy` - 获取类的层次结构
- `GET /api/package/{package_name}/classes` - 获取包中的所有类
- `GET /api/method/{class_name}/{method_name}` - 获取方法详情
- `GET /api/method/{class_name}/{method_name}/examples` - 获取方法示例
- `POST /api/method/{class_name}/{method_name}/examples` - 添加方法示例
- `POST /api/examples/{id}/vote` - 为示例投票
- `PATCH /api/examples/{id}/status` - 更新示例状态

### 版本管理

- `GET /api/v1/versions` - 列出可用版本
- `GET /api/v1/versions/default` - 获取默认版本

## 环境变量

| 变量 | 默认值 | 描述 |
|------|--------|------|
| `GHIDRA_RAG_DATA_DIR` | `./data` | 数据库目录 |
| `GHIDRA_RAG_DEFAULT_VERSION` | `11.3.2` | 默认 Ghidra 版本 |
| `GHIDRA_RAG_HOST` | `0.0.0.0` | 服务器主机 |
| `GHIDRA_RAG_PORT` | `8000` | 服务器端口 |

## 许可证

MIT