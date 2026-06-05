import sqlite3
from datetime import datetime

DB_NAME = "chat_history.db"


def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)


# ---------------------------
# Table Creation
# ---------------------------

def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        hashed_password TEXT NOT NULL,
        is_verified INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS otp_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        otp TEXT NOT NULL,
        expires_at TIMESTAMP NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        video_id TEXT NOT NULL,
        title TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(chat_id) REFERENCES chats(id)
    )
    """)

    conn.commit()
    conn.close()


# ---------------------------
# User Functions
# ---------------------------

def create_user(email: str, hashed_password: str) -> int:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO users (email, hashed_password) VALUES (?, ?)",
        (email, hashed_password)
    )

    user_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return user_id


def get_user_by_email(email: str) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, email, hashed_password, is_verified FROM users WHERE email = ?",
        (email,)
    )

    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return {
        "id": row[0],
        "email": row[1],
        "hashed_password": row[2],
        "is_verified": row[3]
    }


def mark_user_verified(email: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE users SET is_verified = 1 WHERE email = ?",
        (email,)
    )

    conn.commit()
    conn.close()


# ---------------------------
# OTP Functions
# ---------------------------

def save_otp(email: str, otp: str, expires_at: datetime):
    conn = get_connection()
    cursor = conn.cursor()

    # Delete any existing OTPs for this email first
    cursor.execute("DELETE FROM otp_tokens WHERE email = ?", (email,))

    cursor.execute(
        "INSERT INTO otp_tokens (email, otp, expires_at) VALUES (?, ?, ?)",
        (email, otp, expires_at.strftime("%Y-%m-%d %H:%M:%S"))
    )

    conn.commit()
    conn.close()


def get_otp(email: str) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT otp, expires_at FROM otp_tokens WHERE email = ? ORDER BY created_at DESC LIMIT 1",
        (email,)
    )

    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return {
        "otp": row[0],
        "expires_at": datetime.strptime(row[1], "%Y-%m-%d %H:%M:%S")
    }


def delete_otp(email: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM otp_tokens WHERE email = ?", (email,))

    conn.commit()
    conn.close()


# ---------------------------
# Chat Functions
# ---------------------------

def create_chat(user_id: int, video_id: str, title: str) -> int:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO chats (user_id, video_id, title) VALUES (?, ?, ?)",
        (user_id, video_id, title)
    )

    chat_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return chat_id


def get_user_chats(user_id: int) -> list:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, video_id, title, created_at
        FROM chats
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        (user_id,)
    )

    chats = cursor.fetchall()
    conn.close()

    return chats


def update_chat_title(chat_id: int, new_title: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE chats SET title = ? WHERE id = ?",
        (new_title, chat_id)
    )

    conn.commit()
    conn.close()


def delete_chat(chat_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
    cursor.execute("DELETE FROM chats WHERE id = ?", (chat_id,))

    conn.commit()
    conn.close()


# ---------------------------
# Message Functions
# ---------------------------

def save_message(chat_id: int, role: str, content: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO messages (chat_id, role, content) VALUES (?, ?, ?)",
        (chat_id, role, content)
    )

    conn.commit()
    conn.close()


def get_chat_messages(chat_id: int) -> list:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT role, content
        FROM messages
        WHERE chat_id = ?
        ORDER BY created_at ASC
        """,
        (chat_id,)
    )

    messages = cursor.fetchall()
    conn.close()

    return messages