from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from ..services.api_service import api_service
from ..config import get_default_version

router = APIRouter(prefix="/api", tags=["api"])


class MethodExampleCreate(BaseModel):
    example_code: str
    description: Optional[str] = None
    scenario: Optional[str] = None
    expected_output: Optional[str] = None
    author: str = "llm"
    model_id: Optional[str] = None
    confidence: float = 0.5


class VoteRequest(BaseModel):
    vote: str


class StatusUpdateRequest(BaseModel):
    status: str


@router.get("/class/{class_name}/methods")
def get_class_methods(
    class_name: str,
    version: str = Query(default=None)
):
    if version is None:
        version = get_default_version()
    methods = api_service.get_class_methods(class_name, version)
    return {"class_name": class_name, "version": version, "methods": methods}


@router.get("/class/{class_name}/fields")
def get_class_fields(
    class_name: str,
    version: str = Query(default=None)
):
    if version is None:
        version = get_default_version()
    fields = api_service.get_class_fields(class_name, version)
    return {"class_name": class_name, "version": version, "fields": fields}


@router.get("/class/{class_name}/hierarchy")
def get_class_hierarchy(
    class_name: str,
    version: str = Query(default=None)
):
    if version is None:
        version = get_default_version()
    hierarchy = api_service.get_class_hierarchy(class_name, version)
    return {"class_name": class_name, "version": version, "hierarchy": hierarchy}


@router.get("/package/{package_name}/classes")
def get_package_classes(
    package_name: str,
    version: str = Query(default=None)
):
    if version is None:
        version = get_default_version()
    classes = api_service.get_classes_in_package(package_name, version)
    return {"package_name": package_name, "version": version, "classes": classes}


@router.get("/method/{class_name}/{method_name}")
def get_method_detail(
    class_name: str,
    method_name: str,
    version: str = Query(default=None)
):
    if version is None:
        version = get_default_version()
    method = api_service.get_method_detail(class_name, method_name, version)
    if not method:
        raise HTTPException(status_code=404, detail="Method not found")
    return {"class_name": class_name, "method_name": method_name, "version": version, "method": method}


@router.get("/method/{class_name}/{method_name}/examples")
def get_method_examples(
    class_name: str,
    method_name: str,
    version: str = Query(default=None)
):
    if version is None:
        version = get_default_version()
    examples = api_service.get_method_examples(class_name, method_name, version)
    return {"class_name": class_name, "method_name": method_name, "version": version, "examples": examples}


@router.post("/method/{class_name}/{method_name}/examples")
def add_method_example(
    class_name: str,
    method_name: str,
    example: MethodExampleCreate,
    version: str = Query(default=None)
):
    if version is None:
        version = get_default_version()
    result = api_service.add_method_example(
        class_name=class_name,
        method_name=method_name,
        version=version,
        example_code=example.example_code,
        description=example.description,
        scenario=example.scenario,
        expected_output=example.expected_output,
        author=example.author,
        model_id=example.model_id,
        confidence=example.confidence
    )
    if not result:
        raise HTTPException(status_code=404, detail="Class or method not found")
    return {"message": "Example added", "example": result}


@router.post("/examples/{example_id}/vote")
def vote_example(example_id: int, vote: VoteRequest):
    success = api_service.vote_example(example_id, vote.vote)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid vote")
    return {"message": "Vote recorded"}


@router.patch("/examples/{example_id}/status")
def update_example_status(example_id: int, update: StatusUpdateRequest):
    success = api_service.update_example_status(example_id, update.status)
    if not success:
        raise HTTPException(status_code=404, detail="Example not found")
    return {"message": "Status updated"}
