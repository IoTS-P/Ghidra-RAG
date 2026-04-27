from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..services.version_service import version_service

router = APIRouter(prefix="/api/v1", tags=["versions"])


class VersionCreate(BaseModel):
    version: str
    docs_path: str


@router.get("/versions")
def list_versions():
    versions = version_service.list_versions()
    return {"versions": versions}


@router.get("/versions/default")
def get_default_version():
    version = version_service.get_default_version()
    return {"default_version": version}


@router.post("/versions")
def create_version(version_data: VersionCreate):
    result = version_service.add_version(
        version=version_data.version,
        docs_path=version_data.docs_path
    )
    return {"message": "Version added", "version": result}
