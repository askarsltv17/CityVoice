from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any
from urllib.parse import quote

import psycopg
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from psycopg.rows import dict_row

BASE_DIR = Path(__file__).resolve().parent
LEGACY_INSTANCE_DIR = BASE_DIR / "instance"

TABLE_ORDER = [
  "users",
  "complaints",
  "petitions",
  "petition_votes",
  "comments",
  "reactions",
  "moderation_reports",
  "notifications",
  "password_resets",
]


def resolve_instance_dir() -> Path:
  override_dir = os.environ.get("CITYVOICE_INSTANCE_DIR", "").strip()
  if override_dir:
    return Path(override_dir).expanduser()

  local_app_data = os.environ.get("LOCALAPPDATA", "").strip()
  if local_app_data:
    return Path(local_app_data) / "CityVoice" / "instance"

  return LEGACY_INSTANCE_DIR


INSTANCE_DIR = resolve_instance_dir()
DATABASE_PATH = INSTANCE_DIR / "cityvoice.db"


def build_database_url() -> str:
  direct_url = os.environ.get("CITYVOICE_DATABASE_URL", "").strip() or os.environ.get("DATABASE_URL", "").strip()
  if direct_url:
    return direct_url

  host = os.environ.get("CITYVOICE_POSTGRES_HOST", "127.0.0.1").strip() or "127.0.0.1"
  port = os.environ.get("CITYVOICE_POSTGRES_PORT", "5432").strip() or "5432"
  database = os.environ.get("CITYVOICE_POSTGRES_DB", "cityvoice").strip() or "cityvoice"
  user = os.environ.get("CITYVOICE_POSTGRES_USER", "postgres").strip() or "postgres"
  password = quote(os.environ.get("CITYVOICE_POSTGRES_PASSWORD", "postgres"), safe="")
  return f"postgresql://{quote(user, safe='')}:{password}@{host}:{port}/{quote(database, safe='')}"


def _convert_qmark_placeholders(query: str) -> str:
  converted: list[str] = []
  in_single_quote = False
  in_double_quote = False
  index = 0

  while index < len(query):
    char = query[index]

    if char == "'" and not in_double_quote:
      converted.append(char)
      if in_single_quote and index + 1 < len(query) and query[index + 1] == "'":
        converted.append(query[index + 1])
        index += 2
        continue
      in_single_quote = not in_single_quote
      index += 1
      continue

    if char == '"' and not in_single_quote:
      converted.append(char)
      in_double_quote = not in_double_quote
      index += 1
      continue

    if char == "?" and not in_single_quote and not in_double_quote:
      converted.append("%s")
    else:
      converted.append(char)
    index += 1

  return "".join(converted)


def _split_sql_statements(script: str) -> list[str]:
  statements: list[str] = []
  current: list[str] = []
  in_single_quote = False
  in_double_quote = False
  index = 0

  while index < len(script):
    char = script[index]

    if char == "'" and not in_double_quote:
      current.append(char)
      if in_single_quote and index + 1 < len(script) and script[index + 1] == "'":
        current.append(script[index + 1])
        index += 2
        continue
      in_single_quote = not in_single_quote
      index += 1
      continue

    if char == '"' and not in_single_quote:
      current.append(char)
      in_double_quote = not in_double_quote
      index += 1
      continue

    if char == ";" and not in_single_quote and not in_double_quote:
      statement = "".join(current).strip()
      if statement:
        statements.append(statement)
      current = []
      index += 1
      continue

    current.append(char)
    index += 1

  tail = "".join(current).strip()
  if tail:
    statements.append(tail)
  return statements


class CursorWrapper:
  def __init__(self, cursor: psycopg.Cursor):
    self._cursor = cursor

  def execute(self, query: str, params: Any = None):
    sql = _convert_qmark_placeholders(query) if params is not None else query
    if params is None:
      self._cursor.execute(sql)
    else:
      self._cursor.execute(sql, params)
    return self

  def executemany(self, query: str, params_seq):
    sql = _convert_qmark_placeholders(query)
    self._cursor.executemany(sql, params_seq)
    return self

  def executescript(self, script: str):
    for statement in _split_sql_statements(script):
      self._cursor.execute(statement)
    return self

  def fetchone(self):
    return self._cursor.fetchone()

  def fetchall(self):
    return self._cursor.fetchall()

  def close(self) -> None:
    self._cursor.close()

  @property
  def rowcount(self) -> int:
    return self._cursor.rowcount


class ConnectionWrapper:
  def __init__(self, connection: psycopg.Connection):
    self._connection = connection

  def cursor(self) -> CursorWrapper:
    return CursorWrapper(self._connection.cursor())

  def execute(self, query: str, params: Any = None) -> CursorWrapper:
    cursor = self.cursor()
    return cursor.execute(query, params)

  def commit(self) -> None:
    self._connection.commit()

  def rollback(self) -> None:
    self._connection.rollback()

  def close(self) -> None:
    self._connection.close()


def connect_db() -> ConnectionWrapper:
  database_url = build_database_url()
  _create_database_if_missing(database_url)
  try:
    connection = psycopg.connect(database_url, row_factory=dict_row)
  except psycopg.OperationalError as error:
    sqlstate = getattr(error, "sqlstate", None)
    if sqlstate != "3D000" and "does not exist" not in str(error).lower():
      raise
    _create_database_if_missing(database_url)
    connection = psycopg.connect(database_url, row_factory=dict_row)
  return ConnectionWrapper(connection)


def _create_database_if_missing(database_url: str) -> None:
  conninfo = conninfo_to_dict(database_url)
  target_db = conninfo.get("dbname")
  if not target_db or target_db == "postgres":
    return

  maintenance_conninfo = dict(conninfo)
  maintenance_conninfo["dbname"] = "postgres"
  maintenance_url = make_conninfo(**maintenance_conninfo)
  safe_db_name = '"' + target_db.replace('"', '""') + '"'

  with psycopg.connect(maintenance_url, autocommit=True, row_factory=dict_row) as connection:
    exists = connection.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target_db,)).fetchone()
    if exists is None:
      connection.execute(f"CREATE DATABASE {safe_db_name}")


def initialize_database(db: ConnectionWrapper) -> None:
  statements = [
    """
    CREATE TABLE IF NOT EXISTS users (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      email TEXT NOT NULL UNIQUE,
      password_hash TEXT NOT NULL,
      role TEXT NOT NULL DEFAULT 'user',
      last_name TEXT DEFAULT '',
      first_name TEXT DEFAULT '',
      middle_name TEXT DEFAULT '',
      birth_year INTEGER,
      avatar_data TEXT DEFAULT '',
      created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS complaints (
      id TEXT PRIMARY KEY,
      title TEXT NOT NULL,
      category TEXT NOT NULL,
      district TEXT NOT NULL,
      description TEXT NOT NULL,
      status TEXT NOT NULL,
      author_id TEXT NOT NULL REFERENCES users(id),
      latitude DOUBLE PRECISION,
      longitude DOUBLE PRECISION,
      created_at TEXT NOT NULL,
      updated_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS petitions (
      id TEXT PRIMARY KEY,
      title TEXT NOT NULL,
      category TEXT NOT NULL,
      district TEXT NOT NULL DEFAULT '',
      description TEXT NOT NULL,
      goal INTEGER NOT NULL,
      votes INTEGER NOT NULL DEFAULT 0,
      status TEXT NOT NULL,
      author_id TEXT NOT NULL REFERENCES users(id),
      created_at TEXT NOT NULL,
      updated_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS petition_votes (
      id TEXT PRIMARY KEY,
      petition_id TEXT NOT NULL REFERENCES petitions(id),
      user_id TEXT NOT NULL REFERENCES users(id),
      created_at TEXT NOT NULL,
      UNIQUE(petition_id, user_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS comments (
      id TEXT PRIMARY KEY,
      content_type TEXT NOT NULL,
      content_id TEXT NOT NULL,
      user_id TEXT NOT NULL REFERENCES users(id),
      body TEXT NOT NULL,
      created_at TEXT NOT NULL,
      updated_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS reactions (
      id TEXT PRIMARY KEY,
      content_type TEXT NOT NULL,
      content_id TEXT NOT NULL,
      user_id TEXT NOT NULL REFERENCES users(id),
      emoji TEXT NOT NULL,
      created_at TEXT NOT NULL,
      UNIQUE(content_type, content_id, user_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS moderation_reports (
      id TEXT PRIMARY KEY,
      content_type TEXT NOT NULL,
      content_id TEXT NOT NULL,
      reporter_id TEXT NOT NULL REFERENCES users(id),
      reason TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'pending',
      created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS notifications (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL REFERENCES users(id),
      type TEXT NOT NULL,
      message TEXT NOT NULL,
      link TEXT NOT NULL,
      is_read INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS password_resets (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL REFERENCES users(id),
      token TEXT NOT NULL UNIQUE,
      expires_at TEXT NOT NULL,
      used INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL
    )
    """,
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'user'",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_name TEXT DEFAULT ''",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS first_name TEXT DEFAULT ''",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS middle_name TEXT DEFAULT ''",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS birth_year INTEGER",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_data TEXT DEFAULT ''",
    "ALTER TABLE complaints ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION",
    "ALTER TABLE complaints ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION",
    "ALTER TABLE complaints ADD COLUMN IF NOT EXISTS updated_at TEXT",
    "ALTER TABLE petitions ADD COLUMN IF NOT EXISTS district TEXT DEFAULT ''",
    "ALTER TABLE petitions ADD COLUMN IF NOT EXISTS updated_at TEXT",
  ]

  for statement in statements:
    db.execute(statement)
  db.commit()


def database_is_empty(db: ConnectionWrapper) -> bool:
  row = db.execute("SELECT COUNT(*) AS count FROM users").fetchone()
  return not row or row["count"] == 0


def _sqlite_candidates() -> list[Path]:
  candidates: list[Path] = []
  override = os.environ.get("CITYVOICE_LEGACY_SQLITE_PATH", "").strip()
  if override:
    candidates.append(Path(override).expanduser())
  candidates.extend([DATABASE_PATH, LEGACY_INSTANCE_DIR / "cityvoice.db"])

  unique_candidates: list[Path] = []
  seen: set[Path] = set()
  for candidate in candidates:
    resolved = candidate.resolve()
    if resolved not in seen:
      seen.add(resolved)
      unique_candidates.append(candidate)
  return unique_candidates


def pick_legacy_sqlite_path() -> Path | None:
  existing = [path for path in _sqlite_candidates() if path.exists()]
  if not existing:
    return None
  return max(existing, key=lambda path: (path.stat().st_mtime, path.stat().st_size))


def migrate_legacy_sqlite_data(db: ConnectionWrapper) -> Path | None:
  source_path = pick_legacy_sqlite_path()
  if source_path is None or not database_is_empty(db):
    return None

  source = sqlite3.connect(source_path)
  source.row_factory = sqlite3.Row
  try:
    try:
      source_cursor = source.cursor()
      source_rows: dict[str, list[sqlite3.Row]] = {}
      for table in TABLE_ORDER:
        table_exists = source_cursor.execute(
          "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
          (table,),
        ).fetchone()
        if table_exists is None:
          continue

        source_rows[table] = source_cursor.execute(f"SELECT * FROM {table}").fetchall()

      valid_users = source_rows.get("users", [])
      valid_user_ids = {row["id"] for row in valid_users}

      valid_complaints = [row for row in source_rows.get("complaints", []) if row["author_id"] in valid_user_ids]
      valid_complaint_ids = {row["id"] for row in valid_complaints}

      valid_petitions = [row for row in source_rows.get("petitions", []) if row["author_id"] in valid_user_ids]
      valid_petition_ids = {row["id"] for row in valid_petitions}

      prepared_rows = {
        "users": valid_users,
        "complaints": valid_complaints,
        "petitions": valid_petitions,
        "petition_votes": [
          row for row in source_rows.get("petition_votes", [])
          if row["user_id"] in valid_user_ids and row["petition_id"] in valid_petition_ids
        ],
        "comments": [
          row for row in source_rows.get("comments", [])
          if row["user_id"] in valid_user_ids and (
            (row["content_type"] == "complaint" and row["content_id"] in valid_complaint_ids)
            or (row["content_type"] == "petition" and row["content_id"] in valid_petition_ids)
          )
        ],
        "reactions": [
          row for row in source_rows.get("reactions", [])
          if row["user_id"] in valid_user_ids and (
            (row["content_type"] == "complaint" and row["content_id"] in valid_complaint_ids)
            or (row["content_type"] == "petition" and row["content_id"] in valid_petition_ids)
          )
        ],
        "moderation_reports": [
          row for row in source_rows.get("moderation_reports", [])
          if row["reporter_id"] in valid_user_ids and (
            (row["content_type"] == "complaint" and row["content_id"] in valid_complaint_ids)
            or (row["content_type"] == "petition" and row["content_id"] in valid_petition_ids)
          )
        ],
        "notifications": [row for row in source_rows.get("notifications", []) if row["user_id"] in valid_user_ids],
        "password_resets": [row for row in source_rows.get("password_resets", []) if row["user_id"] in valid_user_ids],
      }

      for table in TABLE_ORDER:
        rows = prepared_rows.get(table, [])
        if not rows:
          continue

        columns = rows[0].keys()
        placeholders = ", ".join(["?"] * len(columns))
        quoted_columns = ", ".join(columns)
        insert_sql = f"INSERT INTO {table} ({quoted_columns}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
        db.cursor().executemany(insert_sql, [tuple(row[column] for column in columns) for row in rows])

      db.commit()
    except sqlite3.DatabaseError as error:
      db.rollback()
      print(f"[CityVoice] Skipping legacy SQLite migration from {source_path}: {error}", flush=True)
      return None
  finally:
    source.close()

  return source_path
