# database.py
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path("selfbot.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT,
            username TEXT,
            first_seen TEXT,
            last_seen TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_user(user_id: int, name: str = None, username: str = None):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    now = datetime.now().isoformat()

    cur.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    exists = cur.fetchone()

    if exists:
        cur.execute(
            "UPDATE users SET name = COALESCE(?, name), username = COALESCE(?, username), last_seen = ? WHERE id = ?",
            (name, username, now, user_id)
        )
    else:
        cur.execute(
            "INSERT INTO users (id, name, username, first_seen, last_seen) VALUES (?, ?, ?, ?, ?)",
            (user_id, name, username, now, now)
        )

    conn.commit()
    conn.close()


def get_user(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, name, username, first_seen, last_seen FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row[0],
        "name": row[1],
        "username": row[2],
        "first_seen": row[3],
        "last_seen": row[4],
    }


def update_last_seen(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    now = datetime.now().isoformat()
    cur.execute("UPDATE users SET last_seen = ? WHERE id = ?", (now, user_id))
    conn.commit()
    conn.close()