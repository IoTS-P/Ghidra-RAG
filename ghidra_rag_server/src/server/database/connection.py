import sqlite3
import sqlite_vec
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from ..config import settings


class DatabaseConnection:
    _instance = None
    _db_path: Path = settings.db_path
    _vec_db_path: Path = settings.vec_db_path

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._ensure_data_dir()
        self._init_databases()

    def _ensure_data_dir(self):
        settings.data_dir.mkdir(parents=True, exist_ok=True)

    def _init_databases(self):
        if not self._db_path.exists():
            self._create_main_db()

    def _create_main_db(self):
        schema_path = Path(__file__).parent / "schema.sql"
        with open(schema_path, "r") as f:
            schema = f.read()
        conn = sqlite3.connect(self._db_path)
        conn.executescript(schema)
        conn.close()

    @contextmanager
    def get_main_connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def get_vec_connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self._vec_db_path)
        sqlite_vec.load(conn)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def get_main_cursor(self):
        return self.get_main_connection().__enter__().cursor()

    def get_vec_cursor(self):
        return self.get_vec_connection().__enter__().cursor()


db = DatabaseConnection()


def get_db():
    return db
