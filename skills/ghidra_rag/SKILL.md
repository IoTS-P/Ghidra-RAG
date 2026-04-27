---
name: ghidra-rag
description: 用于查询 Ghidra 逆向分析工具的 API 文档和使用说明的 RAG 系统，支持多版本切换、API 关系查询、语义搜索。
author: Akiba Team
version: 1.0.0
---

## 技能概述

本技能用于在逆向分析过程中，快速查询 Ghidra 逆向框架的 API 使用方法、类继承关系、文档内容。通过 RAG（检索增强生成）系统，可以进行语义搜索找到相关的 API 和文档。

适用人群：进行固件分析、二进制逆向工程的开发者。

## 使用场景

- 场景1：逆向分析时需要查询某个 Ghidra API 的使用方法
- 场景2：查找特定类有哪些方法和属性
- 场景3：理解 Ghidra 类的继承关系
- 场景4：搜索 Ghidra 用户指南和文档

## 前置条件

1. RAG Server 已部署并运行
2. **查询前需先读取配置文件** `skills/ghidra_rag/config.json`，获取服务器地址

## 核心内容

### 一、服务地址配置

每次发起请求前，读取配置文件获取服务器地址：

```
skills/ghidra_rag/config.json
```

配置文件内容示例：
```json
{
    "rag_server": {
        "host": "localhost",
        "port": 8000,
        "base_url": "http://localhost:8000",
        "version": "11.3.2"
    }
}
```

### 二、可用 API 端点

#### 2.0 获取可用版本列表（首次必查）

**端点**: `GET /api/v1/versions`

**返回**:
```json
{
    "versions": [
        {"version": "11.3.2", "docs_path": "docs/11.3.2"}
    ]
}
```

**重要**：每次开始查询前，**必须先调用此端点**获取可用版本列表，然后根据用户需求或自行判断选择合适的版本。如果用户未指定版本，应询问用户希望使用哪个版本。

---

#### 2.1 语义搜索 API（搜索 API 和文档）

**端点**: `POST /api/v1/api/search` 或 `GET /api/v1/api/search`

**请求体**:
```json
{
    "query": "搜索关键词",
    "top_k": 5,
    "chunk_type": "class" | "method" | null,
    "version": "11.3.2"
}
```

**重要**：必须先通过 `/api/v1/versions` 获取可用版本，version 参数必填，不可使用默认值。

**返回**:
```json
{
    "query": "...",
    "version": "11.3.2",
    "results": [
        {
            "type": "method",
            "class": "ghidra.app.util.bin.format.elf.ElfHeader",
            "method": "parse",
            "signature": "void parse()",
            "score": 0.1472,
            "javadoc": "..."
        }
    ]
}
```

**使用场景**：搜索与关键词相关的 API 类或方法，如 "parse elf file"、"read memory bytes"

---

#### 2.2 文档语义搜索

**端点**: `POST /api/v1/search` 或 `GET /api/v1/search`

**请求体**:
```json
{
    "query": "搜索关键词",
    "top_k": 5,
    "doc_type": "installation" | "user_guide" | "changelog" | null,
    "version": "11.3.2"
}
```

**重要**：version 参数必填，不可使用默认值。

**返回**:
```json
{
    "query": "...",
    "version": "11.3.2",
    "results": [
        {
            "doc_type": "installation",
            "heading": "Ghidra Installation Guide",
            "content": "文档内容...",
            "source_file": "docs/11.3.2/InstallationGuide.html",
            "score": 0.4677
        }
    ]
}
```

**使用场景**：搜索用户指南、安装说明、发布说明等文档

---

#### 2.3 查询类的所有方法

**端点**: `GET /api/v1/classes/{class_name}/methods`

**参数**: `version` - **必填**，Ghidra 版本

**返回**:
```json
{
    "class_name": "ghidra.program.model.listing.Function",
    "methods": [...]
}
```

---

#### 2.4 查询类的所有属性

**端点**: `GET /api/v1/classes/{class_name}/fields`

**返回**:
```json
{
    "class_name": "ghidra.program.model.listing.Function",
    "fields": [
        {
            "name": "propertyName",
            "field_type": "String"
        }
    ]
}
```

---

#### 2.5 查询类继承关系

**端点**: `GET /api/v1/classes/{class_name}/hierarchy`

**返回**:
```json
{
    "class_name": "ghidra.program.model.listing.Function",
    "extends": ["ParentClass", "GrandParentClass"],
    "implements": ["Interface1", "Interface2"]
}
```

---

#### 2.6 获取可用版本列表

**端点**: `GET /api/v1/versions`

**返回**:
```json
{
    "versions": [
        {"version": "11.3.2", "docs_path": "docs/11.3.2"}
    ]
}
```

---

#### 2.7 健康检查

**端点**: `GET /health`

**返回**: `{"status": "healthy"}`

---

### 三、关键说明

- **chunk_type 参数**：可选 `class` 或 `method`，用于限定搜索类型
- **doc_type 参数**：可选 `installation`、`user_guide`、`changelog`、`release_notes`、`documentation`、`guide`、`cheatsheet`
- **类名要求**：必须使用全限定名，如 `ghidra.program.model.listing.Function`
- **version 参数**：不指定时默认使用 `11.3.2`

## 示例

### 示例1：搜索与 ELF 文件解析相关的 API

```
当需要查找如何解析 ELF 文件时：

1. 读取配置: skills/ghidra_rag/config.json 获取 base_url
2. 获取版本: GET {base_url}/api/v1/versions 查看可用版本
3. 选择版本: 如用户未指定，询问用户希望使用哪个版本
4. 发送搜索: POST {base_url}/api/v1/api/search
   Body: {"query": "parse elf header", "top_k": 5, "version": "11.3.2"}
5. 解析返回的 results，找到 score 最高的方法
```

### 示例2：查找类的所有方法

```
当需要了解 Function 类有哪些方法时：

1. 获取版本: GET {base_url}/api/v1/versions
2. 选择版本: 假设用户选择 11.3.2
3. 发送请求: GET {base_url}/api/v1/classes/ghidra.program.model.listing.Function/methods?version=11.3.2
4. 解析返回的 methods 列表
```

### 示例3：搜索安装指南

```
当需要查找 Ghidra 安装说明时：

1. 获取版本: GET {base_url}/api/v1/versions
2. 选择版本: 假设用户选择 11.3.2
3. 发送请求: POST {base_url}/api/v1/search
   Body: {"query": "how to install ghidra", "top_k": 3, "doc_type": "installation", "version": "11.3.2"}
4. 解析返回结果中的 content 和 source_file
```

## 注意事项

1. **版本必须动态获取**：每次查询前必须先调用 `/api/v1/versions` 获取可用版本，用户未指定版本时需询问用户
2. **version 参数必填**：所有查询接口的 `version` 参数不可省略或使用默认值
3. **类名必须全限定**：不能使用简写，如 `Function` 必须写成 `ghidra.program.model.listing.Function`
4. **搜索结果按 score 排序**：score 越高表示相关性越强，通常 > 0.1 为较好匹配
5. **method detail 和 examples 端点**：目前返回固定格式数据，实际示例数据待补充

## 拓展说明

### 相关文件

- `skills/ghidra_rag/config.json` - RAG 服务器配置
- `ghidra_rag_server/` - RAG 服务器源码
- `ghidra_rag_client/` - 客户端 SDK（Python）
