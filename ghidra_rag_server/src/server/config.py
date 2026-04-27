import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings


def get_versioned_db_paths(version: str) -> tuple[Path, Path]:
    base_dir = Path(__file__).parent.parent.parent.parent
    data_dir = base_dir / "data" / version
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "ghidra_rag.db", data_dir / "ghidra_vec.db"


def get_default_db_paths() -> tuple[Path, Path]:
    base_dir = Path(__file__).parent.parent.parent.parent
    data_dir = base_dir / "data"
    return data_dir / "ghidra_rag.db", data_dir / "ghidra_vec.db"


class Settings(BaseSettings):
    project_root: Path = Path(__file__).parent.parent.parent.parent
    docs_dir: Path = Path(__file__).parent.parent.parent.parent / "docs"
    data_dir: Path = Path(__file__).parent.parent.parent.parent / "data"

    default_version: str = "11.3.2"

    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384

    @property
    def db_path(self) -> Path:
        return get_default_db_paths()[0]

    @property
    def vec_db_path(self) -> Path:
        return get_default_db_paths()[1]

    class Config:
        env_prefix = "GHIDRA_RAG_"
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()


def get_docs_version_path(version: str) -> Path:
    version_path = settings.docs_dir / version
    if not version_path.exists():
        raise ValueError(f"Version {version} not found in docs directory")
    return version_path


def get_api_docs_path(version: str) -> Path:
    return get_docs_version_path(version) / "api"


def get_default_version() -> str:
    versions = list_available_versions()
    if not versions:
        return settings.default_version
    if settings.default_version not in versions:
        return versions[0]
    return settings.default_version


def list_available_versions() -> list[str]:
    if not settings.docs_dir.exists():
        return []
    return sorted([d.name for d in settings.docs_dir.iterdir() if d.is_dir()])
