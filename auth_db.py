import os
import sqlite3
import hashlib
import hmac
import json
import uuid
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "hallucination_detector.db")

DEFAULT_ADMIN_USER = os.getenv("ADMIN_USERNAME", "admin").strip()
DEFAULT_ADMIN_PASS = os.getenv("ADMIN_PASSWORD", "admin123").strip()


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def get_db_connection():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def hash_password(password: str, salt: str) -> str:
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations=100000,
    )
    return key.hex()


def verify_password(stored_hash: str, salt: str, provided_password: str) -> bool:
    new_hash = hash_password(provided_password, salt)
    return hmac.compare_digest(stored_hash, new_hash)


def init_db():
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE COLLATE NOCASE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                is_admin INTEGER DEFAULT 0,
                is_blocked INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                last_login TEXT
            );
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                messages_json TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """)

            # Create default admin if no admin exists
            cursor = conn.execute("SELECT id FROM users WHERE is_admin = 1 LIMIT 1;")
            admin_row = cursor.fetchone()
            if not admin_row:
                salt = os.urandom(16).hex()
                p_hash = hash_password(DEFAULT_ADMIN_PASS, salt)
                conn.execute(
                    """
                    INSERT OR IGNORE INTO users (username, password_hash, salt, is_admin, is_blocked, created_at)
                    VALUES (?, ?, ?, 1, 0, ?);
                    """,
                    (DEFAULT_ADMIN_USER, p_hash, salt, now_iso()),
                )
    finally:
        conn.close()


def register_user(username: str, password: str, is_admin: bool = False):
    username = username.strip()
    password = password.strip()

    if len(username) < 3:
        return False, "Username must be at least 3 characters long."
    if len(username) > 30:
        return False, "Username must not exceed 30 characters."
    if not username.replace("_", "").replace("-", "").isalnum():
        return False, "Username may only contain letters, numbers, hyphens, and underscores."
    if len(password) < 4:
        return False, "Password must be at least 4 characters long."

    salt = os.urandom(16).hex()
    p_hash = hash_password(password, salt)

    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.execute("SELECT id FROM users WHERE username = ?;", (username,))
            if cursor.fetchone():
                return False, f"User ID '{username}' is already registered. Please choose another or log in."

            conn.execute(
                """
                INSERT INTO users (username, password_hash, salt, is_admin, is_blocked, created_at, last_login)
                VALUES (?, ?, ?, ?, 0, ?, ?);
                """,
                (username, p_hash, salt, 1 if is_admin else 0, now_iso(), now_iso()),
            )
        return True, "Account registered successfully! You can now log in."
    except sqlite3.IntegrityError:
        return False, f"Username '{username}' already exists."
    except Exception as exc:
        return False, f"Database error: {exc}"
    finally:
        conn.close()


def authenticate_user(username: str, password: str):
    username = username.strip()
    password = password.strip()

    if not username or not password:
        return False, "Please enter both User ID and Password.", None

    conn = get_db_connection()
    try:
        cursor = conn.execute(
            """
            SELECT id, username, password_hash, salt, is_admin, is_blocked, created_at, last_login
            FROM users WHERE username = ?;
            """,
            (username,),
        )
        row = cursor.fetchone()
        if not row:
            return False, "Invalid User ID or Password.", None

        if row["is_blocked"]:
            return False, "🚫 This account has been suspended by the administrator.", None

        if not verify_password(row["password_hash"], row["salt"], password):
            return False, "Invalid User ID or Password.", None

        # Update last login timestamp
        now_ts = now_iso()
        with conn:
            conn.execute("UPDATE users SET last_login = ? WHERE id = ?;", (now_ts, row["id"]))

        user_dict = {
            "id": row["id"],
            "username": row["username"],
            "is_admin": bool(row["is_admin"]),
            "is_blocked": bool(row["is_blocked"]),
            "created_at": row["created_at"],
            "last_login": now_ts,
        }
        return True, "Login successful!", user_dict
    except Exception as exc:
        return False, f"Authentication error: {exc}", None
    finally:
        conn.close()


def load_user_conversations(user_id: int):
    conn = get_db_connection()
    conversations = []
    try:
        cursor = conn.execute(
            """
            SELECT id, title, created_at, updated_at, messages_json
            FROM conversations
            WHERE user_id = ?
            ORDER BY updated_at DESC;
            """,
            (user_id,),
        )
        for row in cursor.fetchall():
            try:
                messages = json.loads(row["messages_json"])
            except Exception:
                messages = []
            conversations.append({
                "id": row["id"],
                "title": row["title"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "messages": messages,
            })
    finally:
        conn.close()
    return conversations


def save_user_conversation(user_id: int, conv: dict):
    if not isinstance(conv, dict) or not conv.get("id"):
        return

    conv_id = conv["id"]
    title = conv.get("title", "New Chat")
    created_at = conv.get("created_at") or now_iso()
    updated_at = conv.get("updated_at") or created_at
    messages = conv.get("messages", [])
    messages_json = json.dumps(messages, ensure_ascii=False)

    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO conversations (id, user_id, title, created_at, updated_at, messages_json)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    updated_at = excluded.updated_at,
                    messages_json = excluded.messages_json;
                """,
                (conv_id, user_id, title, created_at, updated_at, messages_json),
            )
    finally:
        conn.close()


def delete_user_conversation(user_id: int, conv_id: str):
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                "DELETE FROM conversations WHERE id = ? AND user_id = ?;",
                (conv_id, user_id),
            )
    finally:
        conn.close()


def get_all_users_for_admin():
    conn = get_db_connection()
    users = []
    try:
        cursor = conn.execute(
            """
            SELECT 
                u.id, 
                u.username, 
                u.is_admin, 
                u.is_blocked, 
                u.created_at, 
                u.last_login,
                COUNT(c.id) as conversation_count
            FROM users u
            LEFT JOIN conversations c ON u.id = c.user_id
            GROUP BY u.id
            ORDER BY u.created_at DESC;
            """
        )
        for row in cursor.fetchall():
            users.append({
                "id": row["id"],
                "username": row["username"],
                "is_admin": bool(row["is_admin"]),
                "is_blocked": bool(row["is_blocked"]),
                "created_at": row["created_at"],
                "last_login": row["last_login"] or "Never",
                "conversation_count": row["conversation_count"],
            })
    finally:
        conn.close()
    return users


def toggle_user_block(admin_user_id: int, target_user_id: int, block: bool):
    if admin_user_id == target_user_id:
        return False, "You cannot block your own admin account."

    conn = get_db_connection()
    try:
        with conn:
            # Check target user exists and is not super admin
            cursor = conn.execute("SELECT is_admin, username FROM users WHERE id = ?;", (target_user_id,))
            target = cursor.fetchone()
            if not target:
                return False, "Target user not found."
            if target["is_admin"] and block:
                return False, "Cannot block another administrator."

            conn.execute(
                "UPDATE users SET is_blocked = ? WHERE id = ?;",
                (1 if block else 0, target_user_id),
            )
        action_word = "blocked" if block else "unblocked"
        return True, f"User '{target['username']}' has been {action_word} successfully."
    except Exception as exc:
        return False, f"Failed to update user status: {exc}"
    finally:
        conn.close()


def change_user_password(user_id: int, new_password: str):
    new_password = new_password.strip()
    if len(new_password) < 4:
        return False, "New password must be at least 4 characters long."

    salt = os.urandom(16).hex()
    p_hash = hash_password(new_password, salt)

    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                "UPDATE users SET password_hash = ?, salt = ? WHERE id = ?;",
                (p_hash, salt, user_id),
            )
        return True, "Password updated successfully."
    except Exception as exc:
        return False, f"Failed to update password: {exc}"
    finally:
        conn.close()


def change_user_username(user_id: int, new_username: str):
    new_username = new_username.strip()
    if len(new_username) < 3:
        return False, "Username must be at least 3 characters long."
    if len(new_username) > 30:
        return False, "Username must not exceed 30 characters."
    if not new_username.replace("_", "").replace("-", "").isalnum():
        return False, "Username may only contain letters, numbers, hyphens, and underscores."

    conn = get_db_connection()
    try:
        with conn:
            # Check if new username is already used by someone else
            cursor = conn.execute("SELECT id FROM users WHERE username = ? AND id != ?;", (new_username, user_id))
            if cursor.fetchone():
                return False, f"User ID '{new_username}' is already in use. Please pick another."

            conn.execute("UPDATE users SET username = ? WHERE id = ?;", (new_username, user_id))
        return True, f"User ID changed to '{new_username}' successfully."
    except sqlite3.IntegrityError:
        return False, f"User ID '{new_username}' is already taken."
    except Exception as exc:
        return False, f"Failed to update User ID: {exc}"
    finally:
        conn.close()


def verify_and_change_password(user_id: int, current_password: str, new_password: str):
    current_password = current_password.strip()
    new_password = new_password.strip()

    if not current_password:
        return False, "Please enter your current password."
    if len(new_password) < 4:
        return False, "New password must be at least 4 characters long."

    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT password_hash, salt FROM users WHERE id = ?;", (user_id,))
        row = cursor.fetchone()
        if not row:
            return False, "User not found."

        if not verify_password(row["password_hash"], row["salt"], current_password):
            return False, "Current password does not match. Please try again."

        new_salt = os.urandom(16).hex()
        new_hash = hash_password(new_password, new_salt)
        with conn:
            conn.execute(
                "UPDATE users SET password_hash = ?, salt = ? WHERE id = ?;",
                (new_hash, new_salt, user_id),
            )
        return True, "Your password has been changed successfully."
    except Exception as exc:
        return False, f"Failed to change password: {exc}"
    finally:
        conn.close()


def admin_reset_user_password(admin_user_id: int, target_user_id: int, new_password: str):
    new_password = new_password.strip()
    if len(new_password) < 4:
        return False, "New password must be at least 4 characters long."

    conn = get_db_connection()
    try:
        # Check admin credentials
        cur = conn.execute("SELECT is_admin FROM users WHERE id = ?;", (admin_user_id,))
        admin_row = cur.fetchone()
        if not admin_row or not admin_row["is_admin"]:
            return False, "Unauthorized: Admin privileges required."

        # Fetch target user
        cur_t = conn.execute("SELECT username FROM users WHERE id = ?;", (target_user_id,))
        target_row = cur_t.fetchone()
        if not target_row:
            return False, "Target user not found."

        new_salt = os.urandom(16).hex()
        new_hash = hash_password(new_password, new_salt)
        with conn:
            conn.execute(
                "UPDATE users SET password_hash = ?, salt = ? WHERE id = ?;",
                (new_hash, new_salt, target_user_id),
            )
        return True, f"Password for '{target_row['username']}' reset successfully."
    except Exception as exc:
        return False, f"Failed to reset password: {exc}"
    finally:
        conn.close()
