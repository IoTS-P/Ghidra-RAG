from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class GhidraVersion(BaseModel):
    version: str
    docs_path: str
    created_at: Optional[datetime] = None


class Package(BaseModel):
    id: int
    version: str
    name: str
    package_path: str


class ClassInfo(BaseModel):
    id: int
    version: str
    name: str
    full_name: str
    package_id: Optional[int] = None
    extends: Optional[str] = None
    implements: Optional[str] = None
    javadoc: Optional[str] = None
    html_file: Optional[str] = None
    json_file: Optional[str] = None
    has_examples: bool = False


class Parameter(BaseModel):
    name: str
    type_long: str
    type_short: str
    comment: Optional[str] = None


class Method(BaseModel):
    id: int
    class_id: int
    name: str
    signature: str
    return_type: Optional[str] = None
    return_javadoc: Optional[str] = None
    is_static: bool = False
    is_constructor: bool = False
    params: Optional[list[Parameter]] = None
    throws: Optional[list[str]] = None
    javadoc: Optional[str] = None
    has_examples: bool = False


class FieldInfo(BaseModel):
    id: int
    class_id: int
    name: str
    field_type: Optional[str] = None
    is_static: bool = False
    is_final: bool = False
    constant_value: Optional[str] = None
    javadoc: Optional[str] = None


class MethodExample(BaseModel):
    id: int
    method_id: int
    example_code: str
    description: Optional[str] = None
    scenario: Optional[str] = None
    expected_output: Optional[str] = None
    author: Optional[str] = None
    model_id: Optional[str] = None
    confidence: float = 0.5
    status: str = "pending"
    upvotes: int = 0
    downvotes: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DocChunk(BaseModel):
    id: int
    version: str
    doc_type: str
    source_file: str
    chunk_index: int
    heading: Optional[str] = None
    content: str
    chunk_vector: Optional[list[float]] = None


class SearchResult(BaseModel):
    chunk_id: int
    content: str
    heading: Optional[str] = None
    source_file: str
    score: float
    doc_type: str
