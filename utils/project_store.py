import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path


class ProjectStore:
    def __init__(self, database_path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    project_id TEXT PRIMARY KEY,
                    project_json TEXT NOT NULL
                )
                """
            )

    @contextmanager
    def _connection(self):
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def load(self, project_id):
        with self._connection() as connection:
            row = connection.execute(
                "SELECT project_json FROM projects WHERE project_id = ?",
                (project_id,),
            ).fetchone()
        return json.loads(row["project_json"]) if row else None

    def save(self, project_id, project):
        serialized = json.dumps(project, ensure_ascii=False)
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO projects (project_id, project_json)
                VALUES (?, ?)
                ON CONFLICT(project_id) DO UPDATE SET project_json = excluded.project_json
                """,
                (project_id, serialized),
            )

    def delete(self, project_id):
        with self._connection() as connection:
            connection.execute(
                "DELETE FROM projects WHERE project_id = ?",
                (project_id,),
            )
