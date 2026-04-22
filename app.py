import json
import os
import secrets
import sqlite3
import sys
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path

from flask import Flask, g, jsonify, render_template, request, session, url_for
from flask_mail import Mail, Message
from dotenv import load_dotenv
from werkzeug.security import check_password_hash, generate_password_hash

from bad_words import contains_bad_words

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

from db import connect_db, initialize_database, migrate_legacy_sqlite_data
DEFAULT_COMPLAINT_STATUS = "Открыта"
DEFAULT_PETITION_STATUS = "Активна"
REACTION_EMOJIS = ["👍", "❤️", "😡", "😢"]
CITY_CENTER = (42.8746, 74.5698)
COMPLAINT_STATUSES = {"Открыта", "В работе", "Решена"}
PETITION_STATUSES = {"Активна", "На рассмотрении", "Реализована"}
DISTRICT_COORDS = {
  "Первомайский район": (42.8796, 74.5890),
  "Свердловский район": (42.8761, 74.6200),
  "Октябрьский район": (42.8425, 74.6327),
  "Ленинский район": (42.8437, 74.5633),
  "Ош": (40.5283, 72.7985),
  "Джалал-Абад": (40.9333, 73.0000),
  "Каракол": (42.4907, 78.3936),
}
DISTRICT_MIGRATION = {
  "Алмалинский район": "Первомайский район",
  "Бостандыкский район": "Октябрьский район",
  "Ауэзовский район": "Ленинский район",
  "Медеуский район": "Свердловский район",
  "Наурызбайский район": "Ленинский район",
  "Жетысуский район": "Свердловский район",
  "Турксибский район": "Первомайский район",
}
DEMO_EMAILS = {
  "ui-test@example.com",
  "smoke@example.com",
  "tester@example.com",
  "tester2@example.com",
  "tester3@example.com",
  "layout-user@example.com",
  "fresh-user@example.com",
  "alpha-user@example.com",
  "beta-user@example.com",
  "gamma-user@example.com",
  "delta-user@example.com",
}
SMTP_PLACEHOLDER_VALUES = {
  "",
  "сюда_пароль_приложения_16_символов",
  "your_app_password_here",
}
DEMO_SEED_PATH = BASE_DIR / "data" / "demo_seed.json"


def load_demo_seed() -> dict:
  with DEMO_SEED_PATH.open("r", encoding="utf-8") as file:
    return json.load(file)


DEMO_SEED = load_demo_seed()
ADMIN_FIXTURE = DEMO_SEED["admin"]
DEMO_USER_FIXTURES = DEMO_SEED["users"]
DEMO_COMPLAINT_FIXTURES = DEMO_SEED["complaints"]
DEMO_PETITION_FIXTURES = DEMO_SEED["petitions"]
app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["SECRET_KEY"] = os.environ.get("CITYVOICE_SECRET_KEY", "cityvoice-dev-secret")
app.config["JSON_AS_ASCII"] = False
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
app.config["MAIL_SERVER"] = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
app.config["MAIL_PORT"] = int(os.environ.get("MAIL_PORT", "587"))
app.config["MAIL_USE_TLS"] = os.environ.get("MAIL_USE_TLS", "true").lower() in {"1", "true", "yes", "on"}
app.config["MAIL_USE_SSL"] = os.environ.get("MAIL_USE_SSL", "false").lower() in {"1", "true", "yes", "on"}
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME", "")
app.config["MAIL_PASSWORD"] = "".join(os.environ.get("MAIL_PASSWORD", "").split())
app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("CITYVOICE_MAIL_SENDER") or os.environ.get("MAIL_USERNAME") or None
app.config["MAIL_SUPPRESS_SEND"] = os.environ.get("MAIL_SUPPRESS_SEND", "false").lower() in {"1", "true", "yes", "on"}
mail = Mail(app)
app.jinja_env.auto_reload = True


def utc_now() -> str:
  return datetime.now(timezone.utc).isoformat()


def smtp_is_configured() -> bool:
  password = str(app.config.get("MAIL_PASSWORD") or "").strip()
  return bool(
    app.config.get("MAIL_USERNAME")
    and password
    and password not in SMTP_PLACEHOLDER_VALUES
    and app.config.get("MAIL_DEFAULT_SENDER")
  )


def configure_console_output() -> None:
  for stream_name in ("stdout", "stderr"):
    stream = getattr(sys, stream_name, None)
    if hasattr(stream, "reconfigure"):
      try:
        stream.reconfigure(encoding="utf-8", errors="replace")
      except ValueError:
        pass


def log_smtp_status() -> None:
  if smtp_is_configured():
    print("✅ SMTP настроен, письма будут отправляться", flush=True)
  else:
    print("❌ SMTP не настроен — проверь .env файл", flush=True)


def first_forwarded_header(name: str) -> str:
  value = request.headers.get(name, "")
  if not value:
    return ""
  return value.split(",")[0].strip()


def parse_forwarded_header(value: str) -> dict[str, str]:
  if not value:
    return {}
  first_entry = value.split(",")[0].strip()
  parsed: dict[str, str] = {}
  for part in first_entry.split(";"):
    if "=" not in part:
      continue
    key, raw_value = part.split("=", 1)
    parsed[key.strip().lower()] = raw_value.strip().strip("\"")
  return parsed


def build_public_url(path: str) -> str:
  base_url = os.environ.get("CITYVOICE_BASE_URL", "").strip().rstrip("/")
  if base_url:
    return f"{base_url}{path}"

  forwarded = parse_forwarded_header(request.headers.get("Forwarded", ""))
  forwarded_host = first_forwarded_header("X-Forwarded-Host") or forwarded.get("host", "")
  forwarded_proto = first_forwarded_header("X-Forwarded-Proto") or forwarded.get("proto", "")
  forwarded_port = first_forwarded_header("X-Forwarded-Port")
  cf_visitor = request.headers.get("Cf-Visitor", "").replace(" ", "").lower()

  host = forwarded_host or request.host
  proto = forwarded_proto or request.scheme or "http"

  if forwarded_port and ":" not in host and not (
    (proto == "http" and forwarded_port == "80")
    or (proto == "https" and forwarded_port == "443")
  ):
    host = f"{host}:{forwarded_port}"

  if "\"scheme\":\"https\"" in cf_visitor or host.lower().endswith(".trycloudflare.com"):
    proto = "https"

  return f"{proto}://{host}{path}"


def send_password_reset_email(recipient: str, reset_url: str) -> bool:
  if not smtp_is_configured():
    print("[CityVoice] SMTP is not configured; password reset email was skipped.", flush=True)
    return False
  message = Message(
    subject="Сброс пароля CityVoice",
    recipients=[recipient],
    body=(
      "Здравствуйте!\n\n"
      "Мы получили запрос на сброс пароля для CityVoice.\n"
      f"Перейдите по ссылке, чтобы задать новый пароль:\n{reset_url}\n\n"
      "Если это были не вы, просто проигнорируйте это письмо."
    ),
  )
  mail.send(message)
  return True


def get_db() -> sqlite3.Connection:
  if "db" not in g:
    g.db = connect_db()
  return g.db


@app.teardown_appcontext
def close_db(_error) -> None:
  db = g.pop("db", None)
  if db is not None:
    db.close()

def init_db() -> None:
  db = connect_db()
  try:
    initialize_database(db)
    migrate_legacy_sqlite_data(db)
  finally:
    db.close()


def guess_coordinates(district: str, unique_text: str) -> tuple[float, float]:
  base_lat, base_lng = DISTRICT_COORDS.get(district, CITY_CENTER)
  seed = sum(ord(char) for char in (district + unique_text))
  return (
    round(base_lat + (((seed % 20) - 10) * 0.0012), 6),
    round(base_lng + ((((seed // 7) % 20) - 10) * 0.0015), 6),
  )


def build_avatar(name: str, avatar_data: str = "") -> dict:
  if avatar_data:
    return {"type": "image", "src": avatar_data}
  normalized = name.strip() or "User"
  parts = [part for part in normalized.split() if part]
  initials = "".join(part[0] for part in parts[:2]).upper() or normalized[:2].upper()
  palette = [("#2a63ff", "#7ea6ff"), ("#ff7f66", "#ffb2a2"), ("#6b5cff", "#a59bff"), ("#0ea5a4", "#7de1dc")]
  start, end = palette[sum(ord(char) for char in normalized) % len(palette)]
  return {"type": "initials", "initials": initials, "start": start, "end": end}


def compute_user_stats(user_id: str) -> dict:
  db = get_db()
  complaints_count = db.execute("SELECT COUNT(*) AS count FROM complaints WHERE author_id = ?", (user_id,)).fetchone()["count"]
  petitions_count = db.execute("SELECT COUNT(*) AS count FROM petitions WHERE author_id = ?", (user_id,)).fetchone()["count"]
  votes_given = db.execute("SELECT COUNT(*) AS count FROM petition_votes WHERE user_id = ?", (user_id,)).fetchone()["count"]
  publications = complaints_count + petitions_count
  return {
    "complaintsCount": complaints_count,
    "petitionsCount": petitions_count,
    "votesGiven": votes_given,
    "publicationsCount": publications,
    "badge": "Активный житель" if publications > 5 else "",
  }


def row_to_user(row: sqlite3.Row | None) -> dict | None:
  if row is None:
    return None
  name_key = "name" if "name" in row.keys() else "author_name"
  payload = {
    "id": row["id"],
    "name": row[name_key],
    "email": row["email"],
    "role": row["role"] if "role" in row.keys() else "user",
    "lastName": row["last_name"] if "last_name" in row.keys() else "",
    "firstName": row["first_name"] if "first_name" in row.keys() else "",
    "middleName": row["middle_name"] if "middle_name" in row.keys() else "",
    "birthYear": row["birth_year"] if "birth_year" in row.keys() else None,
    "avatarData": row["avatar_data"] if "avatar_data" in row.keys() else "",
    "createdAt": row["created_at"],
  }
  payload["avatar"] = build_avatar(payload["name"], payload["avatarData"])
  payload["stats"] = compute_user_stats(payload["id"])
  return payload


def current_user() -> dict | None:
  user_id = session.get("user_id")
  if not user_id:
    return None
  row = get_db().execute(
    """
    SELECT id, name, email, role, last_name, first_name, middle_name, birth_year, avatar_data, created_at
    FROM users WHERE id = ?
    """,
    (user_id,),
  ).fetchone()
  return row_to_user(row)


def is_admin(user: dict | None) -> bool:
  return bool(user and user["role"] == "admin")


def is_moderator(user: dict | None) -> bool:
  return bool(user and user["role"] in {"admin", "moderator"})


def json_error(message: str, status_code: int):
  response = jsonify({"error": message})
  response.status_code = status_code
  return response


def login_required(handler):
  @wraps(handler)
  def wrapper(*args, **kwargs):
    if current_user() is None:
      return json_error("Нужно войти в аккаунт.", 401)
    return handler(*args, **kwargs)
  return wrapper


def moderator_required(handler):
  @wraps(handler)
  def wrapper(*args, **kwargs):
    user = current_user()
    if user is None:
      return json_error("Нужно войти в аккаунт.", 401)
    if not is_moderator(user):
      return json_error("Недостаточно прав.", 403)
    return handler(*args, **kwargs)
  return wrapper


def admin_required(handler):
  @wraps(handler)
  def wrapper(*args, **kwargs):
    user = current_user()
    if user is None:
      return json_error("Нужно войти в аккаунт.", 401)
    if not is_admin(user):
      return json_error("Недостаточно прав.", 403)
    return handler(*args, **kwargs)
  return wrapper


def create_notification(user_id: str, notification_type: str, message: str, link: str) -> None:
  db = get_db()
  db.execute(
    "INSERT INTO notifications (id, user_id, type, message, link, is_read, created_at) VALUES (?, ?, ?, ?, ?, 0, ?)",
    (str(uuid.uuid4()), user_id, notification_type, message, link, utc_now()),
  )
  db.commit()


def text_has_bad_words(*parts: str) -> bool:
  return any(contains_bad_words(part) for part in parts if part)


def looks_broken_text(*parts: str) -> bool:
  return any(("?" in (part or "")) or ("�" in (part or "")) for part in parts)


def reaction_summary(content_type: str, content_id: str, user_id: str | None) -> tuple[dict, str | None]:
  db = get_db()
  counts = {emoji: 0 for emoji in REACTION_EMOJIS}
  rows = db.execute(
    "SELECT emoji, COUNT(*) AS count FROM reactions WHERE content_type = ? AND content_id = ? GROUP BY emoji",
    (content_type, content_id),
  ).fetchall()
  for row in rows:
    counts[row["emoji"]] = row["count"]
  current = None
  if user_id:
    row = db.execute(
      "SELECT emoji FROM reactions WHERE content_type = ? AND content_id = ? AND user_id = ?",
      (content_type, content_id, user_id),
    ).fetchone()
    current = row["emoji"] if row else None
  return counts, current


def comment_count(content_type: str, content_id: str) -> int:
  return get_db().execute(
    "SELECT COUNT(*) AS count FROM comments WHERE content_type = ? AND content_id = ?",
    (content_type, content_id),
  ).fetchone()["count"]


def parse_content_type(kind: str) -> str | None:
  return {"complaints": "complaint", "petitions": "petition"}.get(kind)


def get_content_row(content_type: str, content_id: str) -> sqlite3.Row | None:
  db = get_db()
  if content_type == "complaint":
    return db.execute(
      """
      SELECT complaints.*, users.name AS author_name, users.email, users.role, users.last_name, users.first_name,
             users.middle_name, users.birth_year, users.avatar_data
      FROM complaints JOIN users ON users.id = complaints.author_id WHERE complaints.id = ?
      """,
      (content_id,),
    ).fetchone()
  return db.execute(
    """
    SELECT petitions.*, users.name AS author_name, users.email, users.role, users.last_name, users.first_name,
           users.middle_name, users.birth_year, users.avatar_data
    FROM petitions JOIN users ON users.id = petitions.author_id WHERE petitions.id = ?
    """,
    (content_id,),
  ).fetchone()


def delete_content(content_type: str, content_id: str) -> None:
  db = get_db()
  db.execute("DELETE FROM comments WHERE content_type = ? AND content_id = ?", (content_type, content_id))
  db.execute("DELETE FROM reactions WHERE content_type = ? AND content_id = ?", (content_type, content_id))
  db.execute("DELETE FROM moderation_reports WHERE content_type = ? AND content_id = ?", (content_type, content_id))
  if content_type == "petition":
    db.execute("DELETE FROM petition_votes WHERE petition_id = ?", (content_id,))
    db.execute("DELETE FROM petitions WHERE id = ?", (content_id,))
  else:
    db.execute("DELETE FROM complaints WHERE id = ?", (content_id,))
  db.commit()


def serialize_comment(row: sqlite3.Row, viewer: dict | None) -> dict:
  author = row_to_user(row)
  return {
    "id": row["id"],
    "body": row["body"],
    "createdAt": row["created_at"],
    "updatedAt": row["updated_at"],
    "authorId": row["user_id"],
    "authorName": row["name"],
    "authorAvatar": author["avatar"],
    "canDelete": bool(viewer and (viewer["id"] == row["user_id"] or is_moderator(viewer))),
  }


def serialize_complaint(row: sqlite3.Row, viewer: dict | None = None) -> dict:
  counts, current_reaction = reaction_summary("complaint", row["id"], viewer["id"] if viewer else None)
  author = row_to_user(row)
  return {
    "id": row["id"],
    "type": "complaint",
    "title": row["title"],
    "category": row["category"],
    "district": row["district"],
    "description": row["description"],
    "status": row["status"],
    "latitude": row["latitude"],
    "longitude": row["longitude"],
    "authorId": row["author_id"],
    "authorName": row["author_name"],
    "authorAvatar": author["avatar"],
    "createdAt": row["created_at"],
    "updatedAt": row["updated_at"],
    "reactionCounts": counts,
    "currentReaction": current_reaction,
    "commentCount": comment_count("complaint", row["id"]),
    "canEdit": bool(viewer and viewer["id"] == row["author_id"]),
    "canDelete": bool(viewer and (viewer["id"] == row["author_id"] or is_moderator(viewer))),
    "canManageStatus": bool(viewer and is_admin(viewer)),
  }


def serialize_petition(row: sqlite3.Row, viewer: dict | None = None) -> dict:
  counts, current_reaction = reaction_summary("petition", row["id"], viewer["id"] if viewer else None)
  author = row_to_user(row)
  has_voted = False
  if viewer:
    vote = get_db().execute(
      "SELECT 1 FROM petition_votes WHERE petition_id = ? AND user_id = ?",
      (row["id"], viewer["id"]),
    ).fetchone()
    has_voted = vote is not None
  return {
    "id": row["id"],
    "type": "petition",
    "title": row["title"],
    "category": row["category"],
    "district": row["district"],
    "description": row["description"],
    "goal": row["goal"],
    "votes": row["votes"],
    "status": row["status"],
    "authorId": row["author_id"],
    "authorName": row["author_name"],
    "authorAvatar": author["avatar"],
    "createdAt": row["created_at"],
    "updatedAt": row["updated_at"],
    "hasVoted": has_voted,
    "reactionCounts": counts,
    "currentReaction": current_reaction,
    "commentCount": comment_count("petition", row["id"]),
    "canEdit": bool(viewer and viewer["id"] == row["author_id"]),
    "canDelete": bool(viewer and (viewer["id"] == row["author_id"] or is_moderator(viewer))),
    "canManageStatus": bool(viewer and is_admin(viewer)),
  }


def seed_db() -> None:
  db = connect_db()
  cursor = db.cursor()
  user_ids_by_email: dict[str, str] = {}

  for fixture in [ADMIN_FIXTURE, *DEMO_USER_FIXTURES]:
    row = cursor.execute("SELECT id FROM users WHERE email = ?", (fixture["email"],)).fetchone()
    if row is None:
      user_id = str(uuid.uuid4())
      cursor.execute(
        """
        INSERT INTO users (id, name, email, password_hash, role, last_name, first_name, middle_name, birth_year, avatar_data, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
          user_id,
          fixture["name"],
          fixture["email"],
          generate_password_hash(fixture["password"]),
          fixture["role"],
          fixture["last_name"],
          fixture["first_name"],
          fixture["middle_name"],
          fixture["birth_year"],
          "",
          utc_now(),
        ),
      )
    else:
      user_id = row["id"]
      cursor.execute(
        """
        UPDATE users
        SET name = ?, password_hash = ?, role = ?, last_name = ?, first_name = ?, middle_name = ?, birth_year = ?
        WHERE id = ?
        """,
        (
          fixture["name"],
          generate_password_hash(fixture["password"]),
          fixture["role"],
          fixture["last_name"],
          fixture["first_name"],
          fixture["middle_name"],
          fixture["birth_year"],
          user_id,
        ),
      )
    user_ids_by_email[fixture["email"]] = user_id

  for fixture in DEMO_COMPLAINT_FIXTURES:
    author_id = user_ids_by_email[fixture["author_email"]]
    existing = cursor.execute(
      "SELECT id FROM complaints WHERE title = ? AND author_id = ?",
      (fixture["title"], author_id),
    ).fetchone()
    if existing is not None:
      continue
    complaint_id = str(uuid.uuid4())
    lat, lng = guess_coordinates(fixture["district"], complaint_id)
    now = utc_now()
    cursor.execute(
      """
      INSERT INTO complaints (id, title, category, district, description, status, author_id, latitude, longitude, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      """,
      (
        complaint_id,
        fixture["title"],
        fixture["category"],
        fixture["district"],
        fixture["description"],
        fixture["status"],
        author_id,
        lat,
        lng,
        now,
        now,
      ),
    )

  for fixture in DEMO_PETITION_FIXTURES:
    author_id = user_ids_by_email[fixture["author_email"]]
    existing = cursor.execute(
      "SELECT id FROM petitions WHERE title = ? AND author_id = ?",
      (fixture["title"], author_id),
    ).fetchone()
    if existing is not None:
      continue
    petition_id = str(uuid.uuid4())
    now = utc_now()
    cursor.execute(
      """
      INSERT INTO petitions (id, title, category, district, description, goal, votes, status, author_id, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      """,
      (
        petition_id,
        fixture["title"],
        fixture["category"],
        fixture["district"],
        fixture["description"],
        fixture["goal"],
        fixture["votes"],
        fixture["status"],
        author_id,
        now,
        now,
      ),
    )
  db.commit()
  db.close()


def cleanup_demo_artifacts() -> None:
  db = connect_db()
  cursor = db.cursor()
  email_list = ", ".join(f"'{email}'" for email in sorted(DEMO_EMAILS))
  cursor.execute(f"DELETE FROM petition_votes WHERE user_id IN (SELECT id FROM users WHERE email IN ({email_list}) OR STRPOS(name, '?') > 0)")
  cursor.execute(f"DELETE FROM comments WHERE user_id IN (SELECT id FROM users WHERE email IN ({email_list}) OR STRPOS(name, '?') > 0) OR STRPOS(body, '?') > 0")
  cursor.execute(f"DELETE FROM reactions WHERE user_id IN (SELECT id FROM users WHERE email IN ({email_list}) OR STRPOS(name, '?') > 0)")
  cursor.execute(f"DELETE FROM moderation_reports WHERE reporter_id IN (SELECT id FROM users WHERE email IN ({email_list}) OR STRPOS(name, '?') > 0)")
  cursor.execute(f"DELETE FROM complaints WHERE author_id IN (SELECT id FROM users WHERE email IN ({email_list}) OR STRPOS(name, '?') > 0) OR title LIKE 'Test %' OR STRPOS(title, '?') > 0 OR STRPOS(category, '?') > 0 OR STRPOS(district, '?') > 0 OR STRPOS(description, '?') > 0")
  cursor.execute(f"DELETE FROM petitions WHERE author_id IN (SELECT id FROM users WHERE email IN ({email_list}) OR STRPOS(name, '?') > 0) OR title LIKE 'Test %' OR STRPOS(title, '?') > 0 OR STRPOS(category, '?') > 0 OR STRPOS(description, '?') > 0")
  cursor.execute(f"DELETE FROM notifications WHERE user_id IN (SELECT id FROM users WHERE email IN ({email_list}) OR STRPOS(name, '?') > 0)")
  cursor.execute(f"DELETE FROM password_resets WHERE user_id IN (SELECT id FROM users WHERE email IN ({email_list}) OR STRPOS(name, '?') > 0)")
  cursor.execute(f"DELETE FROM users WHERE email IN ({email_list}) OR STRPOS(name, '?') > 0")
  db.commit()
  db.close()


def cleanup_kyrgyzstan_localization() -> None:
  db = connect_db()
  cursor = db.cursor()

  for table in ("complaints", "petitions"):
    rows = cursor.execute(f"SELECT id, district FROM {table}").fetchall()
    for row in rows:
      mapped = DISTRICT_MIGRATION.get(row["district"])
      if mapped:
        cursor.execute(f"UPDATE {table} SET district = ? WHERE id = ?", (mapped, row["id"]))

  complaint_rows = cursor.execute("SELECT id, title, description, district FROM complaints").fetchall()
  for row in complaint_rows:
    if contains_bad_words(row["title"]) or contains_bad_words(row["description"]) or looks_broken_text(row["title"], row["description"], row["district"]):
      cursor.execute("DELETE FROM comments WHERE content_type = 'complaint' AND content_id = ?", (row["id"],))
      cursor.execute("DELETE FROM reactions WHERE content_type = 'complaint' AND content_id = ?", (row["id"],))
      cursor.execute("DELETE FROM moderation_reports WHERE content_type = 'complaint' AND content_id = ?", (row["id"],))
      cursor.execute("DELETE FROM complaints WHERE id = ?", (row["id"],))
      continue
    lat, lng = guess_coordinates(row["district"], row["id"])
    cursor.execute("UPDATE complaints SET latitude = ?, longitude = ? WHERE id = ?", (lat, lng, row["id"]))

  petition_rows = cursor.execute("SELECT id, title, description, district FROM petitions").fetchall()
  for row in petition_rows:
    if contains_bad_words(row["title"]) or contains_bad_words(row["description"]) or looks_broken_text(row["title"], row["description"], row["district"]):
      cursor.execute("DELETE FROM comments WHERE content_type = 'petition' AND content_id = ?", (row["id"],))
      cursor.execute("DELETE FROM reactions WHERE content_type = 'petition' AND content_id = ?", (row["id"],))
      cursor.execute("DELETE FROM moderation_reports WHERE content_type = 'petition' AND content_id = ?", (row["id"],))
      cursor.execute("DELETE FROM petition_votes WHERE petition_id = ?", (row["id"],))
      cursor.execute("DELETE FROM petitions WHERE id = ?", (row["id"],))

  comment_rows = cursor.execute("SELECT id, body FROM comments").fetchall()
  for row in comment_rows:
    if contains_bad_words(row["body"]) or looks_broken_text(row["body"]):
      cursor.execute("DELETE FROM comments WHERE id = ?", (row["id"],))

  user_rows = cursor.execute("SELECT id, name FROM users").fetchall()
  for row in user_rows:
    if contains_bad_words(row["name"]) or looks_broken_text(row["name"]):
      cursor.execute("UPDATE users SET name = ? WHERE id = ?", (f"Житель-{row['id'][:4]}", row["id"]))

  aidana = cursor.execute("SELECT id FROM users WHERE email = 'aidana@example.com'").fetchone()
  if aidana:
    cursor.execute(
      """
      UPDATE users
      SET name = ?, last_name = ?, first_name = ?, middle_name = ?, birth_year = ?
      WHERE id = ?
      """,
      ("Айпери", "Токтосунова", "Айпери", "", 2001, aidana["id"]),
    )

  db.commit()
  db.close()


@app.route("/")
def index():
  return render_template("index.html")


@app.route("/privacy")
def privacy():
  return render_template("privacy.html")


@app.route("/reset-password/<token>")
def reset_password_page(token: str):
  return render_template("reset_password.html", token=token)


@app.route("/forgot-password")
def forgot_password_page():
  return render_template("forgot_password.html")


@app.get("/api/me")
def api_me():
  return jsonify({"user": current_user()})


@app.get("/api/complaints")
def api_get_complaints():
  viewer = current_user()
  rows = get_db().execute(
    """
    SELECT complaints.*, users.name AS author_name, users.email, users.role, users.last_name, users.first_name,
           users.middle_name, users.birth_year, users.avatar_data
    FROM complaints JOIN users ON users.id = complaints.author_id ORDER BY complaints.created_at DESC
    """
  ).fetchall()
  return jsonify({"complaints": [serialize_complaint(row, viewer) for row in rows]})


@app.get("/api/petitions")
def api_get_petitions():
  viewer = current_user()
  rows = get_db().execute(
    """
    SELECT petitions.*, users.name AS author_name, users.email, users.role, users.last_name, users.first_name,
           users.middle_name, users.birth_year, users.avatar_data
    FROM petitions JOIN users ON users.id = petitions.author_id ORDER BY petitions.created_at DESC
    """
  ).fetchall()
  return jsonify({"petitions": [serialize_petition(row, viewer) for row in rows]})


@app.post("/api/register")
def api_register():
  data = request.get_json(silent=True) or {}
  name = str(data.get("name", "")).strip()
  email = str(data.get("email", "")).strip().lower()
  password = str(data.get("password", ""))
  if len(name) < 2:
    return json_error("Ник должен содержать минимум 2 символа.", 400)
  if "@" not in email:
    return json_error("Укажите корректный email.", 400)
  if len(password) < 6:
    return json_error("Пароль должен содержать минимум 6 символов.", 400)
  db = get_db()
  if db.execute("SELECT 1 FROM users WHERE lower(name) = lower(?)", (name,)).fetchone():
    return json_error("Этот ник уже занят.", 409)
  if db.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
    return json_error("Пользователь с таким email уже существует.", 409)
  user_id = str(uuid.uuid4())
  created_at = utc_now()
  db.execute(
    """
    INSERT INTO users (id, name, email, password_hash, role, last_name, first_name, middle_name, birth_year, avatar_data, created_at)
    VALUES (?, ?, ?, ?, 'user', '', '', '', NULL, '', ?)
    """,
    (user_id, name, email, generate_password_hash(password), created_at),
  )
  db.commit()
  session["user_id"] = user_id
  row = db.execute("SELECT id, name, email, role, last_name, first_name, middle_name, birth_year, avatar_data, created_at FROM users WHERE id = ?", (user_id,)).fetchone()
  return jsonify({"message": "Аккаунт создан.", "user": row_to_user(row)})


@app.post("/api/login")
def api_login():
  data = request.get_json(silent=True) or {}
  email = str(data.get("email", "")).strip().lower()
  password = str(data.get("password", ""))
  row = get_db().execute(
    "SELECT id, name, email, password_hash, role, last_name, first_name, middle_name, birth_year, avatar_data, created_at FROM users WHERE email = ?",
    (email,),
  ).fetchone()
  if row is None or not check_password_hash(row["password_hash"], password):
    return json_error("Неверный email или пароль.", 401)
  session["user_id"] = row["id"]
  return jsonify({"message": "Вход выполнен.", "user": row_to_user(row)})


@app.post("/api/logout")
def api_logout():
  session.clear()
  return jsonify({"message": "Вы вышли из аккаунта."})


@app.patch("/api/profile")
@login_required
def api_update_profile():
  user = current_user()
  data = request.get_json(silent=True) or {}
  name = str(data.get("name", "")).strip()
  last_name = str(data.get("lastName", "")).strip()
  first_name = str(data.get("firstName", "")).strip()
  middle_name = str(data.get("middleName", "")).strip()
  avatar_data = str(data.get("avatarData", "")).strip()
  raw_birth_year = data.get("birthYear")
  birth_year = None
  if raw_birth_year not in (None, ""):
    try:
      birth_year = int(raw_birth_year)
    except (TypeError, ValueError):
      return json_error("Укажите корректный год рождения.", 400)
    if birth_year < 1900 or birth_year > datetime.now().year:
      return json_error("Укажите корректный год рождения.", 400)
  if len(name) < 2:
    return json_error("Ник должен содержать минимум 2 символа.", 400)
  if avatar_data and not avatar_data.startswith("data:image/"):
    return json_error("Некорректный формат аватара.", 400)
  db = get_db()
  if db.execute("SELECT 1 FROM users WHERE lower(name) = lower(?) AND id != ?", (name, user["id"])).fetchone():
    return json_error("Этот ник уже занят.", 409)
  db.execute(
    "UPDATE users SET name = ?, last_name = ?, first_name = ?, middle_name = ?, birth_year = ?, avatar_data = ? WHERE id = ?",
    (name, last_name, first_name, middle_name, birth_year, avatar_data, user["id"]),
  )
  db.commit()
  row = db.execute("SELECT id, name, email, role, last_name, first_name, middle_name, birth_year, avatar_data, created_at FROM users WHERE id = ?", (user["id"],)).fetchone()
  return jsonify({"message": "Профиль обновлён.", "user": row_to_user(row)})


@app.post("/api/password-reset/request")
def api_password_reset_request():
  data = request.get_json(silent=True) or {}
  email = str(data.get("email", "")).strip().lower()
  if "@" not in email:
    return json_error("Укажите корректный email.", 400)
  db = get_db()
  user = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
  if user:
    token = secrets.token_urlsafe(24)
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    db.execute(
      "INSERT INTO password_resets (id, user_id, token, expires_at, used, created_at) VALUES (?, ?, ?, ?, 0, ?)",
      (str(uuid.uuid4()), user["id"], token, expires_at, utc_now()),
    )
    db.commit()
    reset_url = build_public_url(url_for("reset_password_page", token=token))
    delivered = False
    try:
      delivered = send_password_reset_email(email, reset_url)
    except Exception as error:
      print(f"[CityVoice] SMTP error: {error}", flush=True)
    print(f"[CityVoice] Password reset link: {reset_url}", flush=True)
    if delivered:
      return jsonify({"message": "Если аккаунт существует, ссылка для сброса пароля отправлена на email."})
  return jsonify({"message": "Если аккаунт существует, ссылка для сброса пароля отправлена."})


@app.post("/api/password-reset/confirm/<token>")
def api_password_reset_confirm(token: str):
  data = request.get_json(silent=True) or {}
  password = str(data.get("password", ""))
  if len(password) < 6:
    return json_error("Пароль должен содержать минимум 6 символов.", 400)
  db = get_db()
  row = db.execute("SELECT id, user_id, expires_at, used FROM password_resets WHERE token = ?", (token,)).fetchone()
  if row is None:
    return json_error("Ссылка для сброса пароля недействительна.", 404)
  if row["used"]:
    return json_error("Эта ссылка уже использована.", 400)
  if datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc):
    return json_error("Срок действия ссылки истёк.", 400)
  db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (generate_password_hash(password), row["user_id"]))
  db.execute("UPDATE password_resets SET used = 1 WHERE id = ?", (row["id"],))
  db.commit()
  return jsonify({"message": "Пароль обновлён."})


@app.post("/api/complaints")
@login_required
def api_create_complaint():
  user = current_user()
  data = request.get_json(silent=True) or {}
  title = str(data.get("title", "")).strip()
  category = str(data.get("category", "")).strip()
  district = str(data.get("district", "")).strip()
  description = str(data.get("description", "")).strip()
  if not all([title, category, district, description]):
    return json_error("Заполните все поля жалобы.", 400)
  if text_has_bad_words(title, description):
    return json_error("В тексте жалобы обнаружены недопустимые слова.", 400)
  complaint_id = str(uuid.uuid4())
  created_at = utc_now()
  lat, lng = guess_coordinates(district, complaint_id)
  db = get_db()
  db.execute(
    """
    INSERT INTO complaints (id, title, category, district, description, status, author_id, latitude, longitude, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
    (complaint_id, title, category, district, description, DEFAULT_COMPLAINT_STATUS, user["id"], lat, lng, created_at, created_at),
  )
  db.commit()
  return jsonify({"message": "Жалоба опубликована.", "complaint": serialize_complaint(get_content_row("complaint", complaint_id), user)})


@app.patch("/api/complaints/<complaint_id>")
@login_required
def api_update_complaint(complaint_id: str):
  user = current_user()
  row = get_content_row("complaint", complaint_id)
  if row is None:
    return json_error("Жалоба не найдена.", 404)
  if row["author_id"] != user["id"]:
    return json_error("Редактировать может только автор.", 403)
  data = request.get_json(silent=True) or {}
  title = str(data.get("title", row["title"])).strip()
  category = str(data.get("category", row["category"])).strip()
  district = str(data.get("district", row["district"])).strip()
  description = str(data.get("description", row["description"])).strip()
  if text_has_bad_words(title, description):
    return json_error("В тексте жалобы обнаружены недопустимые слова.", 400)
  lat, lng = guess_coordinates(district, complaint_id)
  get_db().execute(
    "UPDATE complaints SET title = ?, category = ?, district = ?, description = ?, latitude = ?, longitude = ?, updated_at = ? WHERE id = ?",
    (title, category, district, description, lat, lng, utc_now(), complaint_id),
  )
  get_db().commit()
  return jsonify({"message": "Жалоба обновлена.", "complaint": serialize_complaint(get_content_row("complaint", complaint_id), user)})


@app.delete("/api/complaints/<complaint_id>")
@login_required
def api_delete_complaint(complaint_id: str):
  user = current_user()
  row = get_content_row("complaint", complaint_id)
  if row is None:
    return json_error("Жалоба не найдена.", 404)
  if row["author_id"] != user["id"] and not is_moderator(user):
    return json_error("Недостаточно прав.", 403)
  delete_content("complaint", complaint_id)
  return jsonify({"message": "Жалоба удалена."})


@app.post("/api/petitions")
@login_required
def api_create_petition():
  user = current_user()
  data = request.get_json(silent=True) or {}
  title = str(data.get("title", "")).strip()
  category = str(data.get("category", "")).strip()
  district = str(data.get("district", "")).strip()
  description = str(data.get("description", "")).strip()
  try:
    goal = int(data.get("goal", 0))
  except (TypeError, ValueError):
    goal = 0
  if not all([title, category, district, description]):
    return json_error("Заполните все поля петиции.", 400)
  if goal < 10:
    return json_error("Цель по голосам должна быть не меньше 10.", 400)
  if text_has_bad_words(title, description):
    return json_error("В тексте петиции обнаружены недопустимые слова.", 400)
  petition_id = str(uuid.uuid4())
  created_at = utc_now()
  db = get_db()
  db.execute(
    """
    INSERT INTO petitions (id, title, category, district, description, goal, votes, status, author_id, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)
    """,
    (petition_id, title, category, district, description, goal, DEFAULT_PETITION_STATUS, user["id"], created_at, created_at),
  )
  db.commit()
  return jsonify({"message": "Петиция создана.", "petition": serialize_petition(get_content_row("petition", petition_id), user)})


@app.patch("/api/petitions/<petition_id>")
@login_required
def api_update_petition(petition_id: str):
  user = current_user()
  row = get_content_row("petition", petition_id)
  if row is None:
    return json_error("Петиция не найдена.", 404)
  if row["author_id"] != user["id"]:
    return json_error("Редактировать может только автор.", 403)
  data = request.get_json(silent=True) or {}
  title = str(data.get("title", row["title"])).strip()
  category = str(data.get("category", row["category"])).strip()
  district = str(data.get("district", row["district"])).strip()
  description = str(data.get("description", row["description"])).strip()
  try:
    goal = int(data.get("goal", row["goal"]))
  except (TypeError, ValueError):
    return json_error("Укажите корректную цель по голосам.", 400)
  if text_has_bad_words(title, description):
    return json_error("В тексте петиции обнаружены недопустимые слова.", 400)
  get_db().execute(
    "UPDATE petitions SET title = ?, category = ?, district = ?, description = ?, goal = ?, updated_at = ? WHERE id = ?",
    (title, category, district, description, goal, utc_now(), petition_id),
  )
  get_db().commit()
  return jsonify({"message": "Петиция обновлена.", "petition": serialize_petition(get_content_row("petition", petition_id), user)})


@app.delete("/api/petitions/<petition_id>")
@login_required
def api_delete_petition(petition_id: str):
  user = current_user()
  row = get_content_row("petition", petition_id)
  if row is None:
    return json_error("Петиция не найдена.", 404)
  if row["author_id"] != user["id"] and not is_moderator(user):
    return json_error("Недостаточно прав.", 403)
  delete_content("petition", petition_id)
  return jsonify({"message": "Петиция удалена."})


@app.post("/api/petitions/<petition_id>/vote")
@login_required
def api_vote_petition(petition_id: str):
  user = current_user()
  db = get_db()
  row = get_content_row("petition", petition_id)
  if row is None:
    return json_error("Петиция не найдена.", 404)
  if row["status"] != DEFAULT_PETITION_STATUS:
    return json_error("Сейчас голосование по этой петиции недоступно.", 400)
  if db.execute("SELECT 1 FROM petition_votes WHERE petition_id = ? AND user_id = ?", (petition_id, user["id"])).fetchone():
    return json_error("Вы уже поддержали эту петицию.", 409)
  db.execute("INSERT INTO petition_votes (id, petition_id, user_id, created_at) VALUES (?, ?, ?, ?)", (str(uuid.uuid4()), petition_id, user["id"], utc_now()))
  db.execute("UPDATE petitions SET votes = votes + 1, updated_at = ? WHERE id = ?", (utc_now(), petition_id))
  db.commit()
  if row["author_id"] != user["id"]:
    create_notification(row["author_id"], "vote", f"За вашу петицию «{row['title']}» проголосовал новый пользователь.", f"/?tab=petitions&post={petition_id}")
  return jsonify({"message": "Голос учтён.", "petition": serialize_petition(get_content_row("petition", petition_id), user)})


@app.get("/api/<kind>/<content_id>/comments")
def api_get_comments(kind: str, content_id: str):
  content_type = parse_content_type(kind)
  if content_type is None:
    return json_error("Неизвестный тип контента.", 404)
  viewer = current_user()
  rows = get_db().execute(
    """
    SELECT comments.*, users.id AS user_id, users.name, users.email, users.role, users.last_name, users.first_name,
           users.middle_name, users.birth_year, users.avatar_data
    FROM comments JOIN users ON users.id = comments.user_id
    WHERE comments.content_type = ? AND comments.content_id = ? ORDER BY comments.created_at ASC
    """,
    (content_type, content_id),
  ).fetchall()
  return jsonify({"comments": [serialize_comment(row, viewer) for row in rows]})


@app.post("/api/<kind>/<content_id>/comments")
@login_required
def api_create_comment(kind: str, content_id: str):
  content_type = parse_content_type(kind)
  if content_type is None:
    return json_error("Неизвестный тип контента.", 404)
  user = current_user()
  content = get_content_row(content_type, content_id)
  if content is None:
    return json_error("Публикация не найдена.", 404)
  body = str((request.get_json(silent=True) or {}).get("body", "")).strip()
  if len(body) < 2:
    return json_error("Комментарий слишком короткий.", 400)
  if text_has_bad_words(body):
    return json_error("В комментарии обнаружены недопустимые слова.", 400)
  db = get_db()
  comment_id = str(uuid.uuid4())
  now = utc_now()
  db.execute("INSERT INTO comments (id, content_type, content_id, user_id, body, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)", (comment_id, content_type, content_id, user["id"], body, now, now))
  db.commit()
  if content["author_id"] != user["id"]:
    create_notification(content["author_id"], "comment", f"Новый комментарий к публикации «{content['title']}».", f"/?tab={'complaints' if content_type == 'complaint' else 'petitions'}&post={content_id}")
  row = db.execute(
    """
    SELECT comments.*, users.id AS user_id, users.name, users.email, users.role, users.last_name, users.first_name,
           users.middle_name, users.birth_year, users.avatar_data
    FROM comments JOIN users ON users.id = comments.user_id WHERE comments.id = ?
    """,
    (comment_id,),
  ).fetchone()
  return jsonify({"message": "Комментарий добавлен.", "comment": serialize_comment(row, user)})


@app.delete("/api/comments/<comment_id>")
@login_required
def api_delete_comment(comment_id: str):
  user = current_user()
  row = get_db().execute("SELECT * FROM comments WHERE id = ?", (comment_id,)).fetchone()
  if row is None:
    return json_error("Комментарий не найден.", 404)
  if row["user_id"] != user["id"] and not is_moderator(user):
    return json_error("Недостаточно прав.", 403)
  get_db().execute("DELETE FROM comments WHERE id = ?", (comment_id,))
  get_db().commit()
  return jsonify({"message": "Комментарий удалён."})


@app.post("/api/<kind>/<content_id>/reactions")
@login_required
def api_toggle_reaction(kind: str, content_id: str):
  content_type = parse_content_type(kind)
  if content_type is None:
    return json_error("Неизвестный тип контента.", 404)
  user = current_user()
  if get_content_row(content_type, content_id) is None:
    return json_error("Публикация не найдена.", 404)
  emoji = str((request.get_json(silent=True) or {}).get("emoji", "")).strip()
  if emoji not in REACTION_EMOJIS:
    return json_error("Недопустимая реакция.", 400)
  db = get_db()
  existing = db.execute("SELECT id, emoji FROM reactions WHERE content_type = ? AND content_id = ? AND user_id = ?", (content_type, content_id, user["id"])).fetchone()
  if existing and existing["emoji"] == emoji:
    db.execute("DELETE FROM reactions WHERE id = ?", (existing["id"],))
  elif existing:
    db.execute("UPDATE reactions SET emoji = ?, created_at = ? WHERE id = ?", (emoji, utc_now(), existing["id"]))
  else:
    db.execute("INSERT INTO reactions (id, content_type, content_id, user_id, emoji, created_at) VALUES (?, ?, ?, ?, ?, ?)", (str(uuid.uuid4()), content_type, content_id, user["id"], emoji, utc_now()))
  db.commit()
  counts, current_reaction = reaction_summary(content_type, content_id, user["id"])
  return jsonify({"message": "Реакция обновлена.", "reactionCounts": counts, "currentReaction": current_reaction})


@app.post("/api/<kind>/<content_id>/report")
@login_required
def api_report_content(kind: str, content_id: str):
  content_type = parse_content_type(kind)
  if content_type is None:
    return json_error("Неизвестный тип контента.", 404)
  user = current_user()
  if get_content_row(content_type, content_id) is None:
    return json_error("Публикация не найдена.", 404)
  reason = str((request.get_json(silent=True) or {}).get("reason", "")).strip() or "Возможное нарушение правил"
  if text_has_bad_words(reason):
    return json_error("В тексте жалобы обнаружены недопустимые слова.", 400)
  get_db().execute("INSERT INTO moderation_reports (id, content_type, content_id, reporter_id, reason, status, created_at) VALUES (?, ?, ?, ?, ?, 'pending', ?)", (str(uuid.uuid4()), content_type, content_id, user["id"], reason, utc_now()))
  get_db().commit()
  return jsonify({"message": "Жалоба отправлена модератору."})


@app.get("/api/notifications")
@login_required
def api_get_notifications():
  user = current_user()
  db = get_db()
  rows = db.execute("SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 20", (user["id"],)).fetchall()
  unread = db.execute("SELECT COUNT(*) AS count FROM notifications WHERE user_id = ? AND is_read = 0", (user["id"],)).fetchone()["count"]
  return jsonify({"notifications": [{"id": row["id"], "type": row["type"], "message": row["message"], "link": row["link"], "isRead": bool(row["is_read"]), "createdAt": row["created_at"]} for row in rows], "unreadCount": unread})


@app.post("/api/notifications/mark-read")
@login_required
def api_mark_notifications_read():
  get_db().execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (current_user()["id"],))
  get_db().commit()
  return jsonify({"message": "Уведомления отмечены как прочитанные."})


@app.get("/api/moderation/reports")
@moderator_required
def api_get_reports():
  rows = get_db().execute(
    """
    SELECT moderation_reports.*, users.name AS reporter_name
    FROM moderation_reports JOIN users ON users.id = moderation_reports.reporter_id
    WHERE moderation_reports.status = 'pending'
    ORDER BY moderation_reports.created_at DESC
    """
  ).fetchall()
  reports = []
  for row in rows:
    content = get_content_row(row["content_type"], row["content_id"])
    if content is None:
      continue
    reports.append({"id": row["id"], "contentType": row["content_type"], "contentId": row["content_id"], "reason": row["reason"], "status": row["status"], "createdAt": row["created_at"], "reporterName": row["reporter_name"], "postTitle": content["title"]})
  return jsonify({"reports": reports})


@app.post("/api/moderation/reports/<report_id>/approve")
@moderator_required
def api_approve_report(report_id: str):
  get_db().execute("UPDATE moderation_reports SET status = 'approved' WHERE id = ?", (report_id,))
  get_db().commit()
  return jsonify({"message": "Жалоба рассмотрена."})


@app.post("/api/moderation/reports/<report_id>/delete-post")
@moderator_required
def api_delete_post_from_report(report_id: str):
  report = get_db().execute("SELECT * FROM moderation_reports WHERE id = ?", (report_id,)).fetchone()
  if report is None:
    return json_error("Жалоба не найдена.", 404)
  delete_content(report["content_type"], report["content_id"])
  get_db().execute("UPDATE moderation_reports SET status = 'deleted' WHERE id = ?", (report_id,))
  get_db().commit()
  return jsonify({"message": "Публикация удалена модератором."})


@app.patch("/api/admin/complaints/<complaint_id>/status")
@admin_required
def api_admin_update_complaint_status(complaint_id: str):
  row = get_content_row("complaint", complaint_id)
  if row is None:
    return json_error("Жалоба не найдена.", 404)
  status = str((request.get_json(silent=True) or {}).get("status", "")).strip()
  if status not in COMPLAINT_STATUSES:
    return json_error("Недопустимый статус жалобы.", 400)
  get_db().execute("UPDATE complaints SET status = ?, updated_at = ? WHERE id = ?", (status, utc_now(), complaint_id))
  get_db().commit()
  updated_row = get_content_row("complaint", complaint_id)
  admin = current_user()
  if updated_row and updated_row["author_id"] != admin["id"]:
    create_notification(updated_row["author_id"], "status", f"Статус вашей жалобы «{updated_row['title']}» изменён на «{status}».", f"/?tab=complaints&post={complaint_id}")
  return jsonify({"message": "Статус жалобы обновлён.", "complaint": serialize_complaint(updated_row, admin)})


@app.patch("/api/admin/petitions/<petition_id>/status")
@admin_required
def api_admin_update_petition_status(petition_id: str):
  row = get_content_row("petition", petition_id)
  if row is None:
    return json_error("Петиция не найдена.", 404)
  status = str((request.get_json(silent=True) or {}).get("status", "")).strip()
  if status not in PETITION_STATUSES:
    return json_error("Недопустимый статус петиции.", 400)
  get_db().execute("UPDATE petitions SET status = ?, updated_at = ? WHERE id = ?", (status, utc_now(), petition_id))
  get_db().commit()
  updated_row = get_content_row("petition", petition_id)
  admin = current_user()
  if updated_row and updated_row["author_id"] != admin["id"]:
    create_notification(updated_row["author_id"], "status", f"Статус вашей петиции «{updated_row['title']}» изменён на «{status}».", f"/?tab=petitions&post={petition_id}")
  return jsonify({"message": "Статус петиции обновлён.", "petition": serialize_petition(updated_row, admin)})


@app.get("/api/admin/users")
@admin_required
def api_get_users_for_admin():
  rows = get_db().execute(
    "SELECT id, name, email, role, last_name, first_name, middle_name, birth_year, avatar_data, created_at FROM users ORDER BY created_at DESC"
  ).fetchall()
  return jsonify({"users": [row_to_user(row) for row in rows]})


@app.patch("/api/admin/users/<user_id>/role")
@admin_required
def api_update_user_role(user_id: str):
  role = str((request.get_json(silent=True) or {}).get("role", "")).strip()
  if role not in {"user", "moderator", "admin"}:
    return json_error("Недопустимая роль.", 400)
  get_db().execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
  get_db().commit()
  row = get_db().execute("SELECT id, name, email, role, last_name, first_name, middle_name, birth_year, avatar_data, created_at FROM users WHERE id = ?", (user_id,)).fetchone()
  if row is None:
    return json_error("Пользователь не найден.", 404)
  return jsonify({"message": "Роль пользователя обновлена.", "user": row_to_user(row)})


init_db()
seed_db()
cleanup_demo_artifacts()
cleanup_kyrgyzstan_localization()


if __name__ == "__main__":
  configure_console_output()
  log_smtp_status()
  app.run(
    debug=os.environ.get("CITYVOICE_DEBUG") == "1",
    host=os.environ.get("CITYVOICE_HOST", "127.0.0.1"),
    port=int(os.environ.get("CITYVOICE_PORT", "5000")),
  )
