import json
from typing import Optional
from .connection import get_db
from .models import GhidraVersion, Package, ClassInfo, Method, FieldInfo, MethodExample, Parameter


class APIRepository:
    def __init__(self):
        self.db = get_db()

    def get_versions(self) -> list[GhidraVersion]:
        with self.db.get_main_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM ghidra_versions ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [GhidraVersion(**dict(row)) for row in rows]

    def add_version(self, version: str, docs_path: str) -> GhidraVersion:
        with self.db.get_main_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO ghidra_versions (version, docs_path) VALUES (?, ?)",
                (version, docs_path),
            )
            conn.commit()
            return GhidraVersion(version=version, docs_path=docs_path)

    def get_package_by_name(self, package_name: str, version: str) -> Optional[Package]:
        with self.db.get_main_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM packages WHERE name = ? AND version = ?", (package_name, version)
            )
            row = cursor.fetchone()
            if row:
                return Package(**dict(row))
            return None

    def get_classes_in_package(self, package_id: int) -> list[ClassInfo]:
        with self.db.get_main_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM classes WHERE package_id = ?", (package_id,))
            rows = cursor.fetchall()
            return [ClassInfo(**dict(row)) for row in rows]

    def get_class_by_full_name(self, full_name: str, version: str) -> Optional[ClassInfo]:
        with self.db.get_main_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM classes WHERE full_name = ? AND version = ?", (full_name, version)
            )
            row = cursor.fetchone()
            if row:
                return ClassInfo(**dict(row))
            return None

    def get_class_by_id(self, class_id: int) -> Optional[ClassInfo]:
        with self.db.get_main_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM classes WHERE id = ?", (class_id,))
            row = cursor.fetchone()
            if row:
                return ClassInfo(**dict(row))
            return None

    def add_class(self, class_info: ClassInfo) -> int:
        with self.db.get_main_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO classes 
                (version, name, full_name, package_id, extends, implements, 
                 javadoc, html_file, json_file, has_examples)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    class_info.version,
                    class_info.name,
                    class_info.full_name,
                    class_info.package_id,
                    class_info.extends,
                    class_info.implements,
                    class_info.javadoc,
                    class_info.html_file,
                    class_info.json_file,
                    class_info.has_examples,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def get_methods_by_class_id(self, class_id: int) -> list[Method]:
        with self.db.get_main_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM methods WHERE class_id = ?", (class_id,))
            rows = cursor.fetchall()
            methods = []
            for row in rows:
                m = dict(row)
                if m.get("params"):
                    m["params"] = json.loads(m["params"])
                if m.get("throws"):
                    m["throws"] = json.loads(m["throws"])
                methods.append(Method(**m))
            return methods

    def get_method_by_name(self, class_id: int, method_name: str) -> Optional[Method]:
        with self.db.get_main_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM methods WHERE class_id = ? AND name = ?", (class_id, method_name)
            )
            row = cursor.fetchone()
            if row:
                m = dict(row)
                if m.get("params"):
                    m["params"] = json.loads(m["params"])
                if m.get("throws"):
                    m["throws"] = json.loads(m["throws"])
                return Method(**m)
            return None

    def get_method_by_id(self, method_id: int) -> Optional[Method]:
        with self.db.get_main_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM methods WHERE id = ?", (method_id,))
            row = cursor.fetchone()
            if row:
                m = dict(row)
                if m.get("params"):
                    m["params"] = json.loads(m["params"])
                if m.get("throws"):
                    m["throws"] = json.loads(m["throws"])
                return Method(**m)
            return None

    def add_method(self, method: Method) -> int:
        with self.db.get_main_connection() as conn:
            cursor = conn.cursor()
            params_json = (
                json.dumps([p.model_dump() for p in method.params]) if method.params else "[]"
            )
            throws_json = json.dumps(method.throws) if method.throws else "[]"
            cursor.execute(
                """INSERT INTO methods 
                (class_id, name, signature, return_type, return_javadoc, 
                 is_static, is_constructor, params, throws, javadoc, has_examples)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    method.class_id,
                    method.name,
                    method.signature,
                    method.return_type,
                    method.return_javadoc,
                    method.is_static,
                    method.is_constructor,
                    params_json,
                    throws_json,
                    method.javadoc,
                    method.has_examples,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def get_fields_by_class_id(self, class_id: int) -> list[FieldInfo]:
        with self.db.get_main_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM fields WHERE class_id = ?", (class_id,))
            rows = cursor.fetchall()
            return [FieldInfo(**dict(row)) for row in rows]

    def add_field(self, field: FieldInfo) -> int:
        with self.db.get_main_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO fields 
                (class_id, name, field_type, is_static, is_final, constant_value, javadoc)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    field.class_id,
                    field.name,
                    field.field_type,
                    field.is_static,
                    field.is_final,
                    field.constant_value,
                    field.javadoc,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def add_package(self, package: Package) -> int:
        with self.db.get_main_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO packages (version, name, package_path) VALUES (?, ?, ?)",
                (package.version, package.name, package.package_path),
            )
            conn.commit()
            return cursor.lastrowid

    def get_package_id(self, package_name: str, version: str) -> Optional[int]:
        with self.db.get_main_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM packages WHERE name = ? AND version = ?", (package_name, version)
            )
            row = cursor.fetchone()
            return row["id"] if row else None

    def add_package_class_relation(self, package_id: int, class_id: int):
        with self.db.get_main_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO package_class_relations (package_id, class_id) VALUES (?, ?)",
                (package_id, class_id),
            )
            conn.commit()

    def get_class_hierarchy(self, class_id: int) -> dict:
        hierarchy = {"ancestors": [], "descendants": []}
        with self.db.get_main_connection() as conn:
            cursor = conn.cursor()
            current_id = class_id
            visited = set()
            while current_id and current_id not in visited:
                visited.add(current_id)
                cursor.execute(
                    "SELECT id, extends, implements FROM classes WHERE id = ?", (current_id,)
                )
                row = cursor.fetchone()
                if not row:
                    break

                parent_name = None
                if row["extends"]:
                    parent_name = row["extends"]
                elif row["implements"]:
                    implements_list = row["implements"].split(",") if row["implements"] else []
                    if implements_list:
                        parent_name = implements_list[0]

                if parent_name:
                    parent = self.get_class_by_full_name(parent_name, "")
                    if parent:
                        hierarchy["ancestors"].append(parent.full_name)
                        current_id = parent.id
                    else:
                        break
                else:
                    break
        return hierarchy

    def get_examples_by_method_id(self, method_id: int) -> list[MethodExample]:
        with self.db.get_main_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT * FROM method_examples 
                WHERE method_id = ? AND status = 'approved'
                ORDER BY confidence DESC, upvotes DESC""",
                (method_id,),
            )
            rows = cursor.fetchall()
            return [MethodExample(**dict(row)) for row in rows]

    def add_example(self, example: MethodExample) -> int:
        with self.db.get_main_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO method_examples 
                (method_id, example_code, description, scenario, expected_output,
                 author, model_id, confidence, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    example.method_id,
                    example.example_code,
                    example.description,
                    example.scenario,
                    example.expected_output,
                    example.author,
                    example.model_id,
                    example.confidence,
                    example.status,
                ),
            )
            conn.commit()
            method = self.get_method_by_id(example.method_id)
            if method:
                cursor.execute(
                    "UPDATE methods SET has_examples = 1 WHERE id = ?", (example.method_id,)
                )
                conn.commit()
            return cursor.lastrowid

    def vote_example(self, example_id: int, vote: str) -> bool:
        with self.db.get_main_connection() as conn:
            cursor = conn.cursor()
            if vote == "up":
                cursor.execute(
                    "UPDATE method_examples SET upvotes = upvotes + 1 WHERE id = ?", (example_id,)
                )
            elif vote == "down":
                cursor.execute(
                    "UPDATE method_examples SET downvotes = downvotes + 1 WHERE id = ?",
                    (example_id,),
                )
            else:
                return False
            conn.commit()
            return True

    def update_example_status(self, example_id: int, status: str) -> bool:
        with self.db.get_main_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE method_examples SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, example_id),
            )
            conn.commit()
            return cursor.rowcount > 0


api_repository = APIRepository()
