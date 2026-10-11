import json
import sqlite3
from pathlib import Path

DB_DIR = Path(__file__).resolve().parent.parent / "data"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "measurements.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS measurements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                payload TEXT NOT NULL,
                result TEXT NOT NULL
            )
            """
        )


def save_measurement(payload, result) -> int:
    with _connect() as conn:
        cursor = conn.execute(
            "INSERT INTO measurements (payload, result) VALUES (?, ?)",
            (json.dumps(payload, sort_keys=True), json.dumps(result, sort_keys=True)),
        )
        return int(cursor.lastrowid)


def list_measurements(limit: int = 20):
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, created_at, payload, result FROM measurements ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()

    return [
        {
            "id": row["id"],
            "created_at": row["created_at"],
            "payload": json.loads(row["payload"]),
            "result": json.loads(row["result"]),
        }
        for row in rows
    ]


def count_measurements() -> int:
    with _connect() as conn:
        row = conn.execute("SELECT COUNT(*) AS total FROM measurements").fetchone()
        return int(row["total"])


init_db()
