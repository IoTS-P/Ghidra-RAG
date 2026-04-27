import sqlite3
import sqlite_vec
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

from ..config import settings, get_versioned_db_paths


class DatabaseConnection:
    _instance = None
    _version: Optional[str] = None

    def __new__(cls, version: Optional[str] = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
            cls._instance._db_path = None
            cls._instance._vec_db_path = None
        return cls._instance

    def __init__(self, version: Optional[str] = None):
        if self._initialized and (version is None or version == self._version):
            return
        self._version = version
        self._initialized = True
        self._ensure_data_dir()
        self._init_databases()

    def _ensure_data_dir(self):
        if self._version:
            data_dir = settings.data_dir / self._version
        else:
            data_dir = settings.data_dir
        data_dir.mkdir(parents=True, exist_ok=True)

    def _init_databases(self):
        if self._version:
            self._db_path, self._vec_db_path = get_versioned_db_paths(self._version)
        else:
            self._db_path = settings.data_dir / "ghidra_rag.db"
            self._vec_db_path = settings.data_dir / "ghidra_vec.db"
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

    def set_version(self, version: str):
        if version != self._version:
            self.__init__(version)


def get_db(version: Optional[str] = None) -> DatabaseConnection:
    db = DatabaseConnection(version)
    return db
