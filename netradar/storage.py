import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class StorageConfig:
    path: str = "~/.netradar/data.db"
    retention_days: int = 7


class Storage:
    def __init__(self, config: StorageConfig):
        self.path = Path(config.path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.retention_days = config.retention_days
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS measurements (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL    NOT NULL,
                endpoint  TEXT    NOT NULL,
                host      TEXT    NOT NULL,
                rtt_avg   REAL,
                rtt_min   REAL,
                rtt_max   REAL,
                loss_pct  REAL    NOT NULL,
                jitter    REAL
            );
            CREATE INDEX IF NOT EXISTS idx_ts ON measurements(timestamp);
            CREATE INDEX IF NOT EXISTS idx_ep ON measurements(endpoint, timestamp);
        """)
        self._conn.commit()

    def insert(
        self,
        endpoint: str,
        host: str,
        rtt_avg: float | None,
        rtt_min: float | None,
        rtt_max: float | None,
        loss_pct: float,
        jitter: float | None,
        timestamp: float | None = None,
    ) -> None:
        self._conn.execute(
            """INSERT INTO measurements
               (timestamp, endpoint, host, rtt_avg, rtt_min, rtt_max, loss_pct, jitter)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (timestamp or time.time(), endpoint, host,
             rtt_avg, rtt_min, rtt_max, loss_pct, jitter),
        )
        self._conn.commit()

    def purge_old(self) -> None:
        cutoff = time.time() - self.retention_days * 86400
        self._conn.execute("DELETE FROM measurements WHERE timestamp < ?", (cutoff,))
        self._conn.commit()

    def latest_per_endpoint(self) -> list[dict[str, Any]]:
        cursor = self._conn.execute("""
            SELECT endpoint, host, rtt_avg, rtt_min, rtt_max, loss_pct, jitter, timestamp
            FROM measurements
            WHERE id IN (
                SELECT MAX(id) FROM measurements GROUP BY endpoint
            )
            ORDER BY endpoint
        """)
        return [dict(row) for row in cursor.fetchall()]
