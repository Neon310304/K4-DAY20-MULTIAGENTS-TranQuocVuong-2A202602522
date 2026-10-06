import math
import re
import sqlite3
import threading
import time
from pathlib import Path

from ..tools import BaseTool, resolve_path, schema


class QueryDatabaseTool(BaseTool):
    def __init__(self, workspace: Path, connection_string: str | None = None, timeout: float = 2):
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Database timeout must be positive and finite")
        self.workspace = Path(workspace).resolve()
        self.filename = connection_string
        self.db_path = resolve_path(self.workspace, connection_string) if connection_string else None
        self.timeout = timeout
        self.connection = None
        self._lock = threading.RLock()
        super().__init__("query_database", "Run a bounded read-only SQLite SELECT on the configured workspace database.",
                         schema({"query": {"type": "string"},
                                 "limit": {"type": "integer", "minimum": 1, "maximum": 1000}}, ["query"]))

    def validate_input(self, arguments: dict) -> bool:
        super().validate_input(arguments)
        query = arguments["query"]
        if len(query) > 8192 or not re.match(r"^\s*(SELECT|WITH)\b", query, re.I):
            raise ValueError("Only read-only SELECT queries are allowed")
        return True

    @staticmethod
    def _authorize(action, argument_one, argument_two, database, trigger):
        allowed = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE}
        return sqlite3.SQLITE_OK if action in allowed and argument_two != "load_extension" else sqlite3.SQLITE_DENY

    def connect(self) -> sqlite3.Connection:
        with self._lock:
            if self.db_path is None:
                raise ValueError("No SQLite database configured")
            if resolve_path(self.workspace, self.filename) != self.db_path:
                raise ValueError("Database path changed or escapes the workspace")
            if self.connection is None:
                self.connection = sqlite3.connect(self.db_path.as_uri() + "?mode=ro", uri=True,
                                                 timeout=self.timeout, check_same_thread=False)
                self.connection.set_authorizer(self._authorize)
            return self.connection

    def close(self) -> None:
        with self._lock:
            if self.connection is not None:
                self.connection.close()
                self.connection = None

    def _execute(self, arguments: dict) -> dict:
        with self._lock:
            connection = self.connect()
            deadline = time.monotonic() + self.timeout
            steps = 0

            def progress():
                nonlocal steps
                steps += 1
                return int(steps > 1000 or time.monotonic() > deadline)

            connection.set_progress_handler(progress, 1000)
            cursor = connection.cursor()
            try:
                cursor.execute(arguments["query"])
                limit = arguments.get("limit", 500)
                rows = cursor.fetchmany(limit + 1)
                return {"columns": [column[0] for column in cursor.description],
                        "rows": [list(row) for row in rows[:limit]], "truncated": len(rows) > limit}
            finally:
                cursor.close()
                connection.set_progress_handler(None, 0)


class AggregationTool(BaseTool):
    def __init__(self):
        super().__init__("aggregation", "Aggregate supplied finite numbers without evaluating Python expressions.",
                         schema({"values": {"type": "array"},
                                 "operation": {"type": "string", "enum": ["sum", "mean", "min", "max", "count"]}},
                                ["values", "operation"]))

    def validate_input(self, arguments: dict) -> bool:
        super().validate_input(arguments)
        values = arguments["values"]
        if len(values) > 10000 or any(isinstance(value, bool) or not isinstance(value, (int, float))
                                     or not math.isfinite(value) for value in values):
            raise ValueError("values must contain at most 10000 finite numbers")
        if not values and arguments["operation"] not in {"sum", "count"}:
            raise ValueError("This operation requires at least one value")
        return True

    def _execute(self, arguments: dict) -> dict:
        values = arguments["values"]
        operation = arguments["operation"]
        if operation == "count":
            value = len(values)
        elif operation in {"sum", "mean"}:
            value = math.fsum(values)
            if operation == "mean":
                value /= len(values)
        else:
            value = min(values) if operation == "min" else max(values)
        if not math.isfinite(value):
            raise ValueError("Aggregate is not finite")
        return {"operation": operation, "value": value, "count": len(values)}
