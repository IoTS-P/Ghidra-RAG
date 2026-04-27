from typing import Optional
from ..database.api_repository import api_repository
from ..config import list_available_versions, get_default_version


class VersionService:
    def list_versions(self) -> list[dict]:
        versions = api_repository.get_versions()
        if not versions:
            available = list_available_versions()
            result = []
            for v in available:
                result.append({"version": v, "docs_path": f"docs/{v}"})
            return result
        return [{"version": v.version, "docs_path": v.docs_path} for v in versions]

    def get_default_version(self) -> str:
        return get_default_version()

    def add_version(self, version: str, docs_path: str) -> dict:
        result = api_repository.add_version(version, docs_path)
        return {"version": result.version, "docs_path": result.docs_path}


version_service = VersionService()
