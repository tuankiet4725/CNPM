"""Lưu lịch sử cảnh báo vào SQLite."""

import os
import sqlite3
import threading

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT NOT NULL,
    class_name  TEXT NOT NULL,
    label       TEXT NOT NULL,
    level       TEXT NOT NULL,
    confidence  REAL NOT NULL,
    track_id    INTEGER,
    near_person INTEGER NOT NULL DEFAULT 0,
    snapshot    TEXT,
    source      TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_time ON events(timestamp);
"""


class EventDatabase:
    def __init__(self, path):
        if path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.executescript(SCHEMA)

    def add_event(self, alert, source=""):
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO events (timestamp, class_name, label, level, confidence, track_id,"
                " near_person, snapshot, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (alert.timestamp, alert.class_name, alert.label, alert.level, alert.confidence,
                 alert.track_id, int(alert.near_person), alert.snapshot, source),
            )
            self._conn.commit()
            return cur.lastrowid

    def recent(self, limit=50):
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def stats(self):
        with self._lock:
            total = self._conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            by_level = dict(self._conn.execute(
                "SELECT level, COUNT(*) FROM events GROUP BY level").fetchall())
            by_class = dict(self._conn.execute(
                "SELECT label, COUNT(*) FROM events GROUP BY label").fetchall())
        return {"total": total, "by_level": by_level, "by_class": by_class}

    def close(self):
        with self._lock:
            self._conn.close()
