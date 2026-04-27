#!/usr/bin/env python3
"""
Download and process Ghidra documentation automatically.

This script:
1. Fetches Ghidra release info from GitHub
2. Downloads the release zip
3. Extracts documentation (non-API and API)
4. Builds the RAG databases
5. Cleans up temporary files
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Optional

import httpx

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
    with httpx.Client(headers=headers, timeout=30) as client:
        response = client.get(url)
        if response.status_code == 403:
            raise Exception("GitHub API rate limit exceeded. Please try again later or set GHIDRA_DOWNLOAD_TOKEN/GITHUB_TOKEN environment variable.")
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


def list_available_versions() -> list[dict]:
    headers = {"Accept": "application/vnd.github+json"}
    token = get_github_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"{GITHUB_API}/repos/{GHIDRA_REPO}/releases"
    with httpx.Client(headers=headers, timeout=30) as client:
        response = client.get(url)
        if response.status_code == 403:
            raise Exception("GitHub API rate limit exceeded. Please try again later or set GHIDRA_DOWNLOAD_TOKEN/GITHUB_TOKEN environment variable.")
        response.raise_for_status()
        releases = response.json()

    versions = []
    for release in releases:
        tag = release.get("tag_name", "")
        match = re.match(r"Ghidra_(\d+\.\d+\.\d+)_build", tag)
        if match:
            version = match.group(1)
            assets = release.get("assets", [])
            download_url = None
            for asset in assets:
                if asset["name"].startswith(f"ghidra_{version}_PUBLIC") and asset["name"].endswith(".zip"):
                    download_url = asset["browser_download_url"]
                    break
            versions.append({
                "version": version,
                "name": release.get("name", ""),
                "tag": tag,
                "download_url": download_url,
            })
    return sorted(versions, key=lambda x: x["version"], reverse=True)


def download_file(url: str, output_path: Path, progress: bool = True, max_retries: int = 3) -> Path:
    headers = {"Accept": "application/octet-stream"}
    token = get_github_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    for attempt in range(max_retries):
        try:
            with httpx.Client(follow_redirects=True, timeout=300) as client:
                response = client.get(url, headers=headers, timeout=300)
                response.raise_for_status()
                total = int(response.headers.get("content-length", 0))

                output_path.parent.mkdir(parents=True, exist_ok=True)

                with open(output_path, "wb") as f:
                    downloaded = 0
                    for chunk in response.iter_bytes(chunk_size=65536):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress and total > 0:
                            percent = downloaded * 100 // total
                            print(f"\r  Downloaded: {downloaded // (1024*1024)}MB / {total // (1024*1024)}MB ({percent}%)", end="", flush=True)

            if progress:
                print()
            return output_path

        except Exception as e:
            if attempt < max_retries - 1:
                print(f"\n  Download failed (attempt {attempt + 1}/{max_retries}), retrying...")
                import time
                time.sleep(2)
            else:
                raise e


def extract_docs(zip_path: Path, extract_dir: Path, version: str):
    print(f"\nExtracting documentation from {zip_path.name}...")

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

        print(f"  Found {len(doc_files)} documentation files")
        if api_zip_name:
            print(f"  Found API javadoc archive")

        extract_dir.mkdir(parents=True, exist_ok=True)
        extract_dir.chmod(0o755)

        extracted_count = 0
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
                        extracted_count += 1

                        parent = extracted.parent
                        while parent != extract_dir and parent.name.startswith("ghidra_"):
                            try:
                                parent.rmdir()
                            except Exception:
                                break
                            parent = parent.parent
                except Exception as e:
                    print(f"  Warning: Failed to extract {name}: {e}")

        print(f"  Successfully extracted {extracted_count} files")

        if api_zip_name:
            print(f"\n  Extracting API javadoc...")
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
                    print(f"  API javadoc extracted!")
            except Exception as e:
                print(f"  Warning: Failed to extract API javadoc: {e}")

    docs_parent = extract_dir.parent
    for item in docs_parent.iterdir():
        if item.name.startswith("ghidra_") and item != extract_dir:
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                item.unlink()

    for item in extract_dir.iterdir():
        if item.name.startswith("ghidra_"):
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                item.unlink()


def build_databases(version: str, docs_dir: Path, data_dir: Path):
    print(f"\n{'='*60}")
    print(f"Building databases for version {version}")
    print(f"{'='*60}")

    project_root = Path(__file__).parent.parent

    scripts_dir = project_root / "scripts"

    print("\n[1/4] Initializing database...")
    result = subprocess.run(
        [sys.executable, str(scripts_dir / "init_db.py"), "--version", version],
        cwd=project_root,
    )
    if result.returncode != 0:
        print(f"  Warning: init_db.py failed")
    else:
        print(f"  Done")

    print("\n[2/4] Ingesting documentation...")
    result = subprocess.run(
        [sys.executable, str(scripts_dir / "ingest_docs.py"), "--version", version],
        cwd=project_root,
        env={**os.environ, "PYTHONPATH": str(project_root / "ghidra_rag_server" / "src")},
    )
    if result.returncode != 0:
        print(f"  Warning: ingest_docs.py failed")

    print("\n[3/4] Ingesting API...")
    result = subprocess.run(
        [
            sys.executable, str(scripts_dir / "ingest_api.py"),
            "--version", version,
            "--docs-path", str(docs_dir.parent)
        ],
        cwd=project_root,
    )
    if result.returncode != 0:
        print(f"  Warning: ingest_api.py failed")

    print("\n[4/4] Creating API embeddings...")
    result = subprocess.run(
        [sys.executable, str(scripts_dir / "ingest_api_chunks.py"), "--version", version],
        cwd=project_root,
        env={**os.environ, "PYTHONPATH": str(project_root / "ghidra_rag_server" / "src")},
    )
    if result.returncode != 0:
        print(f"  Warning: ingest_api_chunks.py failed")


def main():
    parser = argparse.ArgumentParser(
        description="Download and process Ghidra documentation for RAG system"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    list_parser = subparsers.add_parser("list", help="List available Ghidra versions")

    download_parser = subparsers.add_parser("download", help="Download and process a Ghidra version")
    download_parser.add_argument("version", help="Ghidra version (e.g., 11.3.2)")
    download_parser.add_argument(
        "--docs-dir",
        type=Path,
        default=None,
        help="Directory to extract docs (default: project_root/docs)"
    )
    download_parser.add_argument(
        "--skip-db",
        action="store_true",
        help="Skip database building"
    )
    download_parser.add_argument(
        "--skip-cleanup",
        action="store_true",
        help="Skip cleanup of temporary files"
    )

    args = parser.parse_args()

    if args.command == "list":
        print("Fetching available versions from GitHub...")
        try:
            versions = list_available_versions()
            print(f"\n{'Version':<12} {'Name':<30} {'Tag':<35}")
            print("-" * 80)
            for v in versions:
                print(f"{v['version']:<12} {v['name']:<30} {v['tag']:<35}")
        except Exception as e:
            print(f"Error fetching versions: {e}")
            sys.exit(1)

    elif args.command == "download":
        version = args.version
        project_root = Path(__file__).parent.parent

        docs_dir = args.docs_dir or (project_root / "docs")
        version_docs_dir = docs_dir / version

        print(f"{'='*60}")
        print(f"Ghidra RAG - Download and Process")
        print(f"{'='*60}")
        print(f"Version: {version}")
        print(f"Target docs directory: {version_docs_dir}")

        if version_docs_dir.exists():
            print(f"\nWarning: Documentation for version {version} already exists at {version_docs_dir}")
            response = input("Continue and overwrite? [y/N]: ")
            if response.lower() != "y":
                print("Aborted")
                sys.exit(0)

        print("\n[1/3] Fetching release info from GitHub...")
        try:
            release_info = get_release_info(version)
            print(f"  Release: {release_info['name']}")
            print(f"  Download URL: {release_info['download_url']}")
            print(f"  Size: {release_info['size'] // (1024*1024)} MB")
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)

        temp_dir = tempfile.mkdtemp(prefix="ghidra_download_")
        zip_path = Path(temp_dir) / f"ghidra_{version}.zip"

        try:
            print("\n[2/3] Downloading release...")
            download_file(release_info["download_url"], zip_path)

            print("\n[3/3] Extracting documentation...")
            extract_docs(zip_path, version_docs_dir, version)

            if not args.skip_db:
                data_dir = project_root / "data"
                build_databases(version, version_docs_dir, data_dir)

            if not args.skip_cleanup:
                print("\nCleaning up temporary files...")
                Path(temp_dir).rmdir()

            print(f"\n{'='*60}")
            print(f"Complete!")
            print(f"Documentation extracted to: {version_docs_dir}")
            print(f"Database stored in: data/{version}/")
            print(f"{'='*60}")

        except Exception as e:
            print(f"\nError during processing: {e}")

        finally:
            try:
                if zip_path.exists():
                    zip_path.unlink()
            except Exception:
                pass
            try:
                if Path(temp_dir).exists():
                    shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass

    else:
        parser.print_help()


if __name__ == "__main__":
    main()