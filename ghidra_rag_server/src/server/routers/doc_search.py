from typing import Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel
from ..services.search_service import search_service
from ..config import get_default_version

router = APIRouter(prefix="/api/v1", tags=["search"])


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    doc_type: Optional[str] = None


class APISearchRequest(BaseModel):
    query: str
    top_k: int = 5
    chunk_type: Optional[str] = None


@router.post("/search")
def search_docs(request: SearchRequest, version: str = Query(default=None)):
    if version is None:
        version = get_default_version()
    results = search_service.search(
        query=request.query, version=version, top_k=request.top_k, doc_type=request.doc_type
    )
    return {"query": request.query, "version": version, "results": results}


@router.get("/search")
def search_get(
    q: str = Query(..., alias="q"),
    top_k: int = Query(default=5),
    doc_type: Optional[str] = Query(default=None),
    version: str = Query(default=None),
):
    if version is None:
        version = get_default_version()
    results = search_service.search(query=q, version=version, top_k=top_k, doc_type=doc_type)
    return {"query": q, "version": version, "results": results}


@router.post("/api/search")
def search_api(request: APISearchRequest, version: str = Query(default=None)):
    if version is None:
        version = get_default_version()
    results = search_service.search_api(
        query=request.query, version=version, top_k=request.top_k, chunk_type=request.chunk_type
    )
    return {
        "query": request.query,
        "version": version,
        "chunk_type": request.chunk_type,
        "results": [r.to_dict() for r in results],
    }


@router.get("/api/search")
def search_api_get(
    q: str = Query(..., alias="q"),
    top_k: int = Query(default=5),
    chunk_type: Optional[str] = Query(default=None),
    version: str = Query(default=None),
):
    if version is None:
        version = get_default_version()
    results = search_service.search_api(
        query=q, version=version, top_k=top_k, chunk_type=chunk_type
    )
    return {
        "query": q,
        "version": version,
        "chunk_type": chunk_type,
        "results": [r.to_dict() for r in results],
    }
