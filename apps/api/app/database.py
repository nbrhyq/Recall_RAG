import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .config import get_settings


SCHEMA = """
CREATE TABLE IF NOT EXISTS videos (
  id TEXT PRIMARY KEY,
  url TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  author TEXT NOT NULL,
  collection_name TEXT NOT NULL,
  summary TEXT NOT NULL,
  transcript TEXT NOT NULL,
  duration REAL NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'ready',
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS chunks (
  id TEXT PRIMARY KEY,
  video_id TEXT NOT NULL,
  start_time REAL NOT NULL,
  end_time REAL NOT NULL,
  text TEXT NOT NULL,
  tokens TEXT NOT NULL,
  FOREIGN KEY(video_id) REFERENCES videos(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_chunks_video ON chunks(video_id);
"""


@contextmanager
def connection():
    path = Path(get_settings().database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def initialise() -> None:
    with connection() as conn:
        conn.executescript(SCHEMA)
        video_columns = {row[1] for row in conn.execute("PRAGMA table_info(videos)")}
        if "source_type" not in video_columns:
            conn.execute("ALTER TABLE videos ADD COLUMN source_type TEXT NOT NULL DEFAULT 'video'")
        if "file_name" not in video_columns:
            conn.execute("ALTER TABLE videos ADD COLUMN file_name TEXT")
        if "page_count" not in video_columns:
            conn.execute("ALTER TABLE videos ADD COLUMN page_count INTEGER NOT NULL DEFAULT 0")
        chunk_columns = {row[1] for row in conn.execute("PRAGMA table_info(chunks)")}
        if "page_number" not in chunk_columns:
            conn.execute("ALTER TABLE chunks ADD COLUMN page_number INTEGER")


def row_dict(row: sqlite3.Row) -> dict:
    return dict(row)
