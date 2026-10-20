import sqlite3

from app.db import now_utc, utc_iso


class ProcessedEventModel:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def mark(self, event_id: str, event_type: str) -> bool:
        """Registra o evento e devolve False se ele já tinha sido processado."""
        cursor = self.conn.execute(
            'INSERT OR IGNORE INTO processed_events (event_id, type, processed_at) VALUES (?, ?, ?)',
            (event_id, event_type, utc_iso(now_utc())),
        )
        return cursor.rowcount == 1

    def count(self) -> int:
        return self.conn.execute('SELECT COUNT(*) FROM processed_events').fetchone()[0]
