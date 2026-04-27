import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Optional

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from ..config import settings, list_available_versions

router = APIRouter(prefix="/api/v1", tags=["download"])

GHIDRA_REPO = "NationalSecurityAgency/ghidra"
GITHUB_API = "https://api.github.com"


def get_github_token() -> Optional[str]:
    return os.environ.get("GHIDRA_DOWNLOAD_TOKEN") or os.environ.get("GITHUB_TOKEN")


def get_release_info(version: str) -> dict:
    headers = {"Accept": "application/vnd.github+json"}
    token = get_github_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"{GITHUB_API}/repos/{GHIDRA_REPO}/releases"
    with httpx.Client(headers=headers) as client:
        response = client.get(url)
        response.raise_for_status()
        releases = response.json()

    for release in releases:
        tag = release.get("tag_name", "")
        if tag == f"Ghidra_{version}_build":
            assets = release.get("assets", [])
            for asset in assets:
                if asset["name"].startswith(f"ghidra_{version}_PUBLIC") and asset["name"].endswith(".zip"):
                    return {
                        "tag": tag,
                        "name": release.get("name", ""),
                        "version": version,
                        "download_url": asset["browser_download_url"],
                        "size": asset.get("size", 0),
                    }
    raise ValueError(f"Version {version} not found")


def list_ghidra_versions() -> list[dict]:
    headers = {"Accept": "application/vnd.github+json"}
    token = get_github_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"{GITHUB_API}/repos/{GHIDRA_REPO}/releases"
    with httpx.Client(headers=headers) as client:
        response = client.get(url)
        response.raise_for_status()
        releases = response.json()

    import re
    versions = []
    for release in releases:
        tag = release.get("tag_name", "")
        match = re.match(r"Ghidra_(\d+\.\d+\.\d+)_build", tag)
        if match:
            v = match.group(1)
            assets = release.get("assets", [])
            download_url = None
            for asset in assets:
                if asset["name"].startswith(f"ghidra_{v}_PUBLIC") and asset["name"].endswith(".zip"):
                    download_url = asset["browser_download_url"]
                    break
            versions.append({
                "version": v,
                "name": release.get("name", ""),
                "tag": tag,
                "download_url": download_url,
            })
    return sorted(versions, key=lambda x: x["version"], reverse=True)


class DownloadRequest(BaseModel):
    version: str


class DownloadStatus(BaseModel):
    status: str
    version: Optional[str] = None
    progress: Optional[float] = None
    message: Optional[str] = None


_download_tasks = {}


def download_file(url: str, output_path: Path, progress_callback=None) -> Path:
    headers = {"Accept": "application/octet-stream"}
    token = get_github_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    with httpx.Client(follow_redirects=True) as client:
        with client.stream("GET", url, headers=headers) as response:
            response.raise_for_status()
            total = int(response.headers.get("content-length", 0))

            output_path.parent.mkdir(parents=True, exist_ok=True)

            downloaded = 0
            with open(output_path, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total > 0:
                        progress_callback(downloaded, total)

    return output_path


def extract_docs(zip_path: Path, extract_dir: Path, version: str):
    with zipfile.ZipFile(zip_path, "r") as zf:
        namelist = zf.namelist()

        docs_root_pattern = f"ghidra_{version}_PUBLIC/docs/"
        api_zip_pattern = f"ghidra_{version}_PUBLIC/docs/GhidraAPI_javadoc.zip"

        doc_files = []
        api_zip_name = None

        for name in namelist:
            if name.startswith(docs_root_pattern) and not name.endswith("/"):
                doc_files.append(name)
            if name == api_zip_pattern:
                api_zip_name = name

        extract_dir.mkdir(parents=True, exist_ok=True)

        for name in doc_files:
            target_name = name.replace(docs_root_pattern, "")
            if target_name:
                target_path = extract_dir / target_name
                target_path.parent.mkdir(parents=True, exist_ok=True)

                try:
                    zf.extract(name, extract_dir)
                    extracted = extract_dir / name
                    if extracted.exists():
                        if target_path.exists():
                            target_path.unlink()
                        shutil.move(str(extracted), str(target_path))
                except Exception:
                    pass

        if api_zip_name:
            api_extract_dir = extract_dir / "api"
            if api_extract_dir.exists():
                shutil.rmtree(api_extract_dir, ignore_errors=True)
            api_extract_dir.mkdir(parents=True, exist_ok=True)

            try:
                with zf.open(api_zip_name) as api_zf:
                    api_zip_path = extract_dir / "GhidraAPI_javadoc.zip"
                    with open(api_zip_path, "wb") as f:
                        f.write(api_zf.read())

                    with zipfile.ZipFile(api_zip_path, "r") as api_zip:
                        api_namelist = api_zip.namelist()

                        for name in api_namelist:
                            if name.endswith("/"):
                                continue
                            target_name = name
                            if target_name.startswith("api/"):
                                target_name = target_name[4:]

                            if target_name:
                                target_path = api_extract_dir / target_name
                                target_path.parent.mkdir(parents=True, exist_ok=True)

                                try:
                                    api_zip.extract(name, api_extract_dir)
                                    extracted = api_extract_dir / name
                                    if extracted.exists() and extracted != target_path:
                                        if target_path.exists():
                                            target_path.unlink()
                                        shutil.move(str(extracted), str(target_path))
                                except Exception:
                                    pass

                        def flatten_nested_api(src_dir, dest_dir):
                            if not src_dir.exists():
                                return
                            for item in src_dir.iterdir():
                                if item.is_dir():
                                    flatten_nested_api(item, dest_dir)
                                    try:
                                        item.rmdir()
                                    except Exception:
                                        pass
                                else:
                                    target = dest_dir / item.name
                                    if target.exists():
                                        target.unlink()
                                    try:
                                        shutil.move(str(item), str(target))
                                    except Exception:
                                        pass

                        nested_api = api_extract_dir / "api"
                        if nested_api.exists():
                            flatten_nested_api(nested_api, api_extract_dir)
                            try:
                                shutil.rmtree(nested_api, ignore_errors=True)
                            except Exception:
                                pass

                    api_zip_path.unlink()
            except Exception:
                pass

    docs_parent = extract_dir.parent
    for item in docs_parent.iterdir():
        if item.name.startswith("ghidra_") and item != extract_dir:
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                item.unlink()


def build_databases(version: str, docs_dir: Path):
    project_root = settings.project_root
    scripts_dir = project_root / "scripts"

    subprocess.run(
        [sys.executable, str(scripts_dir / "init_db.py"), "--version", version],
        cwd=project_root,
        env={**os.environ, "PYTHONPATH": str(project_root / "ghidra_rag_server" / "src")},
    )

    subprocess.run(
        [sys.executable, str(scripts_dir / "ingest_docs.py"), "--version", version],
        cwd=project_root,
        env={**os.environ, "PYTHONPATH": str(project_root / "ghidra_rag_server" / "src")},
    )

    subprocess.run(
        [
            sys.executable, str(scripts_dir / "ingest_api.py"),
            "--version", version,
            "--docs-path", str(docs_dir.parent)
        ],
        cwd=project_root,
    )

    subprocess.run(
        [sys.executable, str(scripts_dir / "ingest_api_chunks.py"), "--version", version],
        cwd=project_root,
        env={**os.environ, "PYTHONPATH": str(project_root / "ghidra_rag_server" / "src")},
    )


def process_download(task_id: str, version: str):
    try:
        _download_tasks[task_id] = {"status": "downloading", "progress": 0.0, "message": "Fetching release info..."}

        release_info = get_release_info(version)

        temp_dir = tempfile.mkdtemp(prefix="ghidra_download_")
        zip_path = Path(temp_dir) / f"ghidra_{version}.zip"

        def progress_callback(downloaded: int, total: int):
            _download_tasks[task_id]["progress"] = downloaded / total * 50
            _download_tasks[task_id]["message"] = f"Downloading: {downloaded // (1024*1024)}MB / {total // (1024*1024)}MB"

        _download_tasks[task_id]["status"] = "downloading"
        _download_tasks[task_id]["progress"] = 0.0
        _download_tasks[task_id]["message"] = "Downloading release..."

        download_file(release_info["download_url"], zip_path, progress_callback)

        version_docs_dir = settings.docs_dir / version

        _download_tasks[task_id]["progress"] = 50.0
        _download_tasks[task_id]["message"] = "Extracting documentation..."

        extract_docs(zip_path, version_docs_dir, version)

        _download_tasks[task_id]["progress"] = 70.0
        _download_tasks[task_id]["message"] = "Building databases..."

        build_databases(version, version_docs_dir)

        _download_tasks[task_id]["progress"] = 100.0
        _download_tasks[task_id]["status"] = "completed"
        _download_tasks[task_id]["message"] = "Download and processing complete"

        if zip_path.exists():
            zip_path.unlink()
        if Path(temp_dir).exists():
            shutil.rmtree(temp_dir, ignore_errors=True)

    except Exception as e:
        _download_tasks[task_id] = {
            "status": "failed",
            "progress": 0.0,
            "message": str(e)
        }


@router.get("/download/versions")
def get_available_versions():
    try:
        versions = list_ghidra_versions()
        return {"versions": versions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/download")
def start_download(request: DownloadRequest, background_tasks: BackgroundTasks):
    version = request.version
    version_docs_dir = settings.docs_dir / version

    if version_docs_dir.exists():
        raise HTTPException(
            status_code=409,
            detail=f"Version {version} already exists at {version_docs_dir}"
        )

    task_id = f"download_{version}"
    _download_tasks[task_id] = {"status": "pending", "progress": 0.0, "message": "Starting..."}

    background_tasks.add_task(process_download, task_id, version)

    return {"task_id": task_id, "status": "started", "version": version}


@router.get("/download/status/{task_id}")
def get_download_status(task_id: str):
    if task_id not in _download_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return _download_tasks[task_id]