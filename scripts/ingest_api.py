#!/usr/bin/env python3
import json
import sys
from pathlib import Path
import sqlite3
from bs4 import BeautifulSoup


def get_db_path(version: str):
    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / "data" / version
    data_dir.mkdir(exist_ok=True)
    return data_dir / "ghidra_rag.db"


class APIParser:
    def __init__(self, version: str, docs_path: Path):
        self.version = version
        self.docs_path = docs_path
        self.api_path = docs_path / "api"
        self.processed_classes = 0
        self.processed_methods = 0
        self.processed_fields = 0
        self.conn = sqlite3.connect(get_db_path(version))
        self.conn.row_factory = sqlite3.Row

    def close(self):
        self.conn.close()

    def add_version(self):
        self.conn.execute(
            "INSERT OR REPLACE INTO ghidra_versions (version, docs_path) VALUES (?, ?)",
            (self.version, str(self.docs_path)),
        )
        self.conn.commit()

    def ensure_package(self, package_name: str, package_path: str) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id FROM packages WHERE name = ? AND version = ?", (package_name, self.version)
        )
        row = cursor.fetchone()
        if row:
            return row[0]
        cursor.execute(
            "INSERT INTO packages (version, name, package_path) VALUES (?, ?, ?)",
            (self.version, package_name, package_path),
        )
        self.conn.commit()
        return cursor.lastrowid

    def parse_class_json(self, json_file: Path) -> dict:
        with open(json_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def process_class_json(self, json_data: dict, html_file: str, json_file: str):
        json_file_path = Path(json_file)

        rel_path = json_file_path.relative_to(self.api_path)
        parts = list(rel_path.parts)

        if len(parts) >= 2 and parts[-1].endswith(".json"):
            class_name_from_file = parts[-1].replace(".json", "")
            package_parts = parts[:-1]
            package_name = ".".join(package_parts) if package_parts else ""
        else:
            package_name = ""

        package_path = package_name.replace(".", "/")

        if package_name:
            package_id = self.ensure_package(package_name, package_path)
        else:
            package_id = None

        class_name = json_data.get("name", "")
        if "." not in class_name and package_name:
            full_name = f"{package_name}.{class_name}"
        else:
            full_name = class_name

        extends = json_data.get("extends")
        implements_list = json_data.get("implements", [])
        implements = ",".join(implements_list) if implements_list else None
        javadoc = json_data.get("javadoc") or json_data.get("comment")

        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT INTO classes 
            (version, name, full_name, package_id, extends, implements, javadoc, html_file, json_file, has_examples)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)""",
            (
                self.version,
                class_name,
                full_name,
                package_id,
                extends,
                implements,
                javadoc,
                html_file,
                json_file,
            ),
        )
        class_id = cursor.lastrowid

        if package_id and class_id:
            cursor.execute(
                "INSERT OR IGNORE INTO package_class_relations (package_id, class_id) VALUES (?, ?)",
                (package_id, class_id),
            )

        for field_data in json_data.get("fields", []):
            cursor.execute(
                """INSERT INTO fields 
                (class_id, name, field_type, is_static, is_final, constant_value, javadoc)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    class_id,
                    field_data.get("name", ""),
                    field_data.get("type_long"),
                    field_data.get("static", False),
                    field_data.get("final", False),
                    field_data.get("constant_value"),
                    field_data.get("javadoc") or field_data.get("comment"),
                ),
            )
            self.processed_fields += 1

        for method_data in json_data.get("methods", []):
            params = []
            for p in method_data.get("params", []):
                params.append(
                    {
                        "name": p.get("name", ""),
                        "type_long": p.get("type_long", ""),
                        "type_short": p.get("type_short", ""),
                        "comment": p.get("comment"),
                    }
                )

            throws = []
            for t in method_data.get("throws", []):
                if isinstance(t, dict):
                    throws.append(t.get("type_long", ""))
                else:
                    throws.append(str(t))

            return_info = method_data.get("return", {})
            return_type = return_info.get("type_long") if return_info else None
            return_javadoc = return_info.get("comment") if return_info else None

            signature = self._build_signature(method_data)
            method_name = method_data.get("name", "")

            cursor.execute(
                """INSERT INTO methods 
                (class_id, name, signature, return_type, return_javadoc, is_static, is_constructor, params, throws, javadoc, has_examples)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)""",
                (
                    class_id,
                    method_name,
                    signature,
                    return_type,
                    return_javadoc,
                    method_data.get("static", False),
                    method_name == "<init>",
                    json.dumps(params),
                    json.dumps(throws) if throws else None,
                    method_data.get("javadoc") or method_data.get("comment"),
                ),
            )
            self.processed_methods += 1

        self.processed_classes += 1

    def _build_signature(self, method_data: dict) -> str:
        name = method_data.get("name", "")
        params = method_data.get("params", [])
        param_strs = []
        for p in params:
            ptype = p.get("type_short", p.get("type_long", ""))
            pname = p.get("name", "")
            param_strs.append(f"{ptype} {pname}")
        return f"{name}({', '.join(param_strs)})"

    def ingest(self):
        print(f"Starting API ingestion for version {self.version}")
        print(f"API path: {self.api_path}")

        if not self.api_path.exists():
            print(f"Error: API path {self.api_path} does not exist")
            return False

        self.add_version()

        json_files = list(self.api_path.rglob("*.json"))
        print(f"Found {len(json_files)} JSON files")

        for json_file in json_files:
            try:
                json_data = self.parse_class_json(json_file)
                html_file = str(json_file.with_suffix(".html"))
                self.process_class_json(json_data, html_file, str(json_file))
            except Exception as e:
                print(f"Error processing {json_file}: {e}")

        self.conn.close()

        print(f"\nIngestion complete:")
        print(f"  Classes: {self.processed_classes}")
        print(f"  Methods: {self.processed_methods}")
        print(f"  Fields: {self.processed_fields}")
        return True


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Ingest Ghidra API documentation")
    parser.add_argument("--version", required=True, help="Ghidra version")
    parser.add_argument("--docs-path", required=True, help="Path to docs directory")
    args = parser.parse_args()

    docs_path = Path(args.docs_path)
    if not docs_path.exists():
        print(f"Error: Docs path {docs_path} does not exist")
        sys.exit(1)

    version_path = docs_path / args.version
    if not version_path.exists():
        print(f"Error: Version {args.version} not found in {docs_path}")
        sys.exit(1)

    api_path = version_path / "api"
    if not api_path.exists():
        print(f"Error: API directory not found in {version_path}")
        sys.exit(1)

    parser_instance = APIParser(args.version, version_path)
    success = parser_instance.ingest()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
