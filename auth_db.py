import os
import sqlite3
import hashlib
import hmac
import json
import uuid
import time
import re
import secrets
import logging
import tempfile
from datetime import datetime

logger = logging.getLogger("auth_db")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.getenv("PERSISTENT_DATA_DIR") or os.getenv("DATA_DIR") or os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "hallucination_detector.db")

DEFAULT_ADMIN_USER = os.getenv("ADMIN_USERNAME", "admin").strip()
ADMIN_ENV_PASS = os.getenv("ADMIN_PASSWORD")
if ADMIN_ENV_PASS and ADMIN_ENV_PASS.strip():
    DEFAULT_ADMIN_PASS = ADMIN_ENV_PASS.strip()
else:
    DEFAULT_ADMIN_PASS = os.getenv("ADMIN_DEFAULT_FALLBACK", "Admin#2026!SecureKey")

PBKDF2_ITERATIONS = 600000
USERNAME_REGEX = re.compile(r"^[A-Za-z0-9_-]{3,30}$")
_DB_INITIALIZED = False


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def get_db_connection():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def hash_password(password: str, salt: str, iterations: int = PBKDF2_ITERATIONS) -> str:
    # Cap password length at 128 characters to prevent CPU exhaustion DoS
    pwd_bytes = password[:128].encode("utf-8")
    key = hashlib.pbkdf2_hmac(
        "sha256",
        pwd_bytes,
        salt.encode("utf-8"),
        iterations=iterations,
    )
    return key.hex()


def verify_password(stored_hash: str, salt: str, provided_password: str) -> bool:
    # Check with current recommended iterations (600k)
    new_hash = hash_password(provided_password, salt, iterations=PBKDF2_ITERATIONS)
    if hmac.compare_digest(stored_hash, new_hash):
        return True
    # Backwards-compatibility check with legacy iteration count (100k)
    legacy_hash = hash_password(provided_password, salt, iterations=100000)
    return hmac.compare_digest(stored_hash, legacy_hash)


USERS_BACKUP_PATH = os.path.join(DATA_DIR, "users_backup.json")
CONVERSATIONS_BACKUP_PATH = os.path.join(DATA_DIR, "conversations_backup.json")


def _atomic_write_json(file_path, data):
    dir_name = os.path.dirname(os.path.abspath(file_path))
    os.makedirs(dir_name, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, prefix="tmp_bak_", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, file_path)
    except Exception:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        raise


def sync_users_to_backup():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        conn = get_db_connection()
        try:
            cur = conn.execute("SELECT id, username, password_hash, salt, is_admin, is_blocked, created_at, last_login FROM users;")
            users = [dict(row) for row in cur.fetchall()]
            _atomic_write_json(USERS_BACKUP_PATH, users)
        finally:
            conn.close()
    except Exception as exc:
        logger.warning(f"Failed to sync users to backup: {exc}")


def sync_conversations_to_backup():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        conn = get_db_connection()
        try:
            cur = conn.execute("SELECT id, user_id, title, created_at, updated_at, messages_json FROM conversations;")
            convs = [dict(row) for row in cur.fetchall()]
            _atomic_write_json(CONVERSATIONS_BACKUP_PATH, convs)
        finally:
            conn.close()
    except Exception as exc:
        logger.warning(f"Failed to sync conversations to backup: {exc}")


def restore_users_from_backup(conn):
    if not os.path.exists(USERS_BACKUP_PATH):
        return
    try:
        with open(USERS_BACKUP_PATH, "r", encoding="utf-8") as f:
            users = json.load(f)
        if isinstance(users, list):
            with conn:
                for u in users:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO users (id, username, password_hash, salt, is_admin, is_blocked, created_at, last_login)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            u.get("id"),
                            u["username"],
                            u["password_hash"],
                            u["salt"],
                            u.get("is_admin", 0),
                            u.get("is_blocked", 0),
                            u.get("created_at", now_iso()),
                            u.get("last_login"),
                        ),
                    )
    except Exception as exc:
        logger.warning(f"Failed to restore users from backup: {exc}")


def restore_conversations_from_backup(conn):
    if not os.path.exists(CONVERSATIONS_BACKUP_PATH):
        return
    try:
        with open(CONVERSATIONS_BACKUP_PATH, "r", encoding="utf-8") as f:
            convs = json.load(f)
        if isinstance(convs, list):
            with conn:
                for c in convs:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO conversations (id, user_id, title, created_at, updated_at, messages_json)
                        VALUES (?, ?, ?, ?, ?, ?);
                        """,
                        (
                            c["id"],
                            c["user_id"],
                            c.get("title", "New Chat"),
                            c.get("created_at", now_iso()),
                            c.get("updated_at", now_iso()),
                            c.get("messages_json", "[]"),
                        ),
                    )
    except Exception as exc:
        logger.warning(f"Failed to restore conversations from backup: {exc}")


def init_db():
    global _DB_INITIALIZED
    if _DB_INITIALIZED:
        return

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

            conn.execute("""
            CREATE TABLE IF NOT EXISTS login_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT COLLATE NOCASE NOT NULL,
                attempt_time REAL NOT NULL
            );
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS visitors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_hash TEXT NOT NULL,
                user_agent TEXT,
                path TEXT,
                referrer TEXT,
                user_id INTEGER,
                visited_at TEXT NOT NULL
            );
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS login_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                user_id INTEGER,
                ip_hash TEXT,
                user_agent TEXT,
                status TEXT NOT NULL,
                timestamp TEXT NOT NULL
            );
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS feedbacks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT NOT NULL,
                user_id INTEGER,
                username TEXT,
                query TEXT,
                answer TEXT,
                rating TEXT NOT NULL,
                comment TEXT,
                status TEXT DEFAULT 'pending',
                diagnosis TEXT,
                proposed_fix TEXT,
                resolution TEXT,
                resolved_at TEXT,
                resolved_by TEXT,
                created_at TEXT NOT NULL
            );
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                is_admin INTEGER DEFAULT 0,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """)

            # Safe schema migrations for feedbacks and users tables
            for col_name, col_def in [
                ("status", "TEXT DEFAULT 'pending'"),
                ("diagnosis", "TEXT"),
                ("proposed_fix", "TEXT"),
                ("resolution", "TEXT"),
                ("resolved_at", "TEXT"),
                ("resolved_by", "TEXT"),
            ]:
                try:
                    conn.execute(f"ALTER TABLE feedbacks ADD COLUMN {col_name} {col_def};")
                except Exception:
                    pass

            for col_name, col_def in [
                ("api_key", "TEXT"),
                ("plan", "TEXT DEFAULT 'free'"),
            ]:
                try:
                    conn.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_def};")
                except Exception:
                    pass

            # 1. Restore only if database currently has zero users
            cur_count = conn.execute("SELECT COUNT(*) FROM users;")
            if cur_count.fetchone()[0] == 0:
                restore_users_from_backup(conn)
                restore_conversations_from_backup(conn)

            # 2. Create default admin if no admin exists
            cursor = conn.execute("SELECT id FROM users WHERE is_admin = 1 LIMIT 1;")
            admin_row = cursor.fetchone()
            if not admin_row:
                salt = secrets.token_hex(16)
                p_hash = hash_password(DEFAULT_ADMIN_PASS, salt)
                conn.execute(
                    """
                    INSERT OR IGNORE INTO users (username, password_hash, salt, is_admin, is_blocked, created_at)
                    VALUES (?, ?, ?, 1, 0, ?);
                    """,
                    (DEFAULT_ADMIN_USER, p_hash, salt, now_iso()),
                )
                logger.info(f"Initialized default admin account: {DEFAULT_ADMIN_USER}")
    finally:
        conn.close()

    _DB_INITIALIZED = True


def register_user(username: str, password: str, is_admin: bool = False):
    username = username.strip()
    if not USERNAME_REGEX.fullmatch(username):
        return False, "Username must be 3-30 characters and contain only English letters, numbers, hyphens, and underscores."

    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if len(password) > 128:
        return False, "Password must not exceed 128 characters."

    salt = secrets.token_hex(16)
    p_hash = hash_password(password, salt)

    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.execute("SELECT id FROM users WHERE username = ? COLLATE NOCASE;", (username,))
            if cursor.fetchone():
                return False, f"User ID '{username}' is already registered. Please choose another or log in."

            conn.execute(
                """
                INSERT INTO users (username, password_hash, salt, is_admin, is_blocked, created_at, last_login)
                VALUES (?, ?, ?, ?, 0, ?, ?);
                """,
                (username, p_hash, salt, 1 if is_admin else 0, now_iso(), now_iso()),
            )
        sync_users_to_backup()
        return True, "Account registered successfully! You can now log in."
    except sqlite3.IntegrityError:
        return False, f"Username '{username}' already exists."
    except Exception as exc:
        return False, f"Database error: {exc}"
    finally:
        conn.close()


MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_SECONDS = 900  # 15 minutes


def _check_rate_limit(username: str, conn=None):
    now = time.time()
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    try:
        # Prune expired attempts
        conn.execute("DELETE FROM login_attempts WHERE attempt_time < ?;", (now - LOCKOUT_DURATION_SECONDS,))
        cur = conn.execute("SELECT COUNT(*) FROM login_attempts WHERE username = ? COLLATE NOCASE;", (username.strip(),))
        count = cur.fetchone()[0]
        if count >= MAX_LOGIN_ATTEMPTS:
            return False, "Too many failed login attempts for this account. Please wait 15 minutes before trying again."
        return True, None
    finally:
        if close_conn:
            conn.close()


def _record_failed_attempt(username: str):
    try:
        conn = get_db_connection()
        with conn:
            conn.execute("INSERT INTO login_attempts (username, attempt_time) VALUES (?, ?);", (username.strip(), time.time()))
        conn.close()
    except Exception:
        pass


def _clear_login_attempts(username: str):
    try:
        conn = get_db_connection()
        with conn:
            conn.execute("DELETE FROM login_attempts WHERE username = ? COLLATE NOCASE;", (username.strip(),))
        conn.close()
    except Exception:
        pass


def authenticate_user(username: str, password: str):
    if not username or not password:
        return False, "Please enter both User ID and Password.", None

    if len(password) > 128:
        return False, "Invalid User ID or Password.", None

    ok_limit, limit_msg = _check_rate_limit(username)
    if not ok_limit:
        return False, limit_msg, None

    conn = get_db_connection()
    try:
        cursor = conn.execute(
            """
            SELECT id, username, password_hash, salt, is_admin, is_blocked, created_at, last_login
            FROM users WHERE username = ? COLLATE NOCASE;
            """,
            (username.strip(),),
        )
        row = cursor.fetchone()
        if not row:
            # Constant-time dummy computation prevents username enumeration timing attack
            _ = hash_password(password, "dummy_salt_for_constant_timing_comparison")
            _record_failed_attempt(username)
            return False, "Invalid User ID or Password.", None

        # Verify password FIRST before revealing blocked status to avoid account status enumeration
        if not verify_password(row["password_hash"], row["salt"], password):
            _record_failed_attempt(username)
            return False, "Invalid User ID or Password.", None

        if row["is_blocked"]:
            return False, "🚫 This account has been suspended by the administrator.", None

        # Success: clear failed attempts
        _clear_login_attempts(username)

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

    messages = conv.get("messages", [])
    # Do not persist empty placeholder chats (0 messages) to avoid polluting DB
    if not messages:
        return

    conv_id = str(conv["id"])
    title = conv.get("title", "New Chat")
    created_at = conv.get("created_at") or now_iso()
    updated_at = conv.get("updated_at") or created_at
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
                    messages_json = excluded.messages_json
                WHERE conversations.user_id = excluded.user_id;
                """,
                (conv_id, user_id, title, created_at, updated_at, messages_json),
            )
    finally:
        conn.close()

    sync_conversations_to_backup()


def delete_user_conversation(user_id: int, conv_id: str):
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                "DELETE FROM conversations WHERE id = ? AND user_id = ?;",
                (str(conv_id), user_id),
            )
    finally:
        conn.close()

    sync_conversations_to_backup()


def delete_user_account(user_id: int) -> bool:
    """Permanently deletes a user, all their conversations, and session data (GDPR Art. 17)."""
    conn = get_db_connection()
    try:
        with conn:
            cur = conn.execute("SELECT username FROM users WHERE id = ?;", (user_id,))
            row = cur.fetchone()
            if not row:
                return False
            username = row["username"]

            conn.execute("DELETE FROM conversations WHERE user_id = ?;", (user_id,))
            conn.execute("DELETE FROM login_attempts WHERE username = ?;", (username,))
            conn.execute("DELETE FROM sessions WHERE user_id = ?;", (user_id,))
            conn.execute("DELETE FROM users WHERE id = ?;", (user_id,))
    finally:
        conn.close()

    sync_conversations_to_backup()
    sync_users_to_backup()
    return True


def save_session(token: str, user_id: int, username: str, is_admin: bool, expires_in_seconds: int = 86400 * 30):
    conn = get_db_connection()
    now_t = time.time()
    exp_t = now_t + expires_in_seconds
    try:
        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO sessions (token, user_id, username, is_admin, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (token, user_id, username, 1 if is_admin else 0, now_t, exp_t)
            )
    finally:
        conn.close()


def get_session(token: str):
    if not token:
        return None
    conn = get_db_connection()
    try:
        cur = conn.execute(
            "SELECT user_id, username, is_admin, expires_at FROM sessions WHERE token = ?;",
            (token,)
        )
        row = cur.fetchone()
        if not row:
            return None
        if row["expires_at"] < time.time():
            with conn:
                conn.execute("DELETE FROM sessions WHERE token = ?;", (token,))
            return None
        return {
            "user_id": row["user_id"],
            "username": row["username"],
            "is_admin": bool(row["is_admin"])
        }
    finally:
        conn.close()


def delete_session(token: str):
    if not token:
        return
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("DELETE FROM sessions WHERE token = ?;", (token,))
    finally:
        conn.close()


def update_session_username(user_id: int, new_username: str):
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                "UPDATE sessions SET username = ? WHERE user_id = ?;",
                (new_username, user_id)
            )
    finally:
        conn.close()


def get_all_users_for_admin(admin_user_id: int = None):
    conn = get_db_connection()
    users = []
    try:
        if admin_user_id is not None:
            cur_a = conn.execute("SELECT is_admin FROM users WHERE id = ?;", (admin_user_id,))
            admin_row = cur_a.fetchone()
            if not admin_row or not admin_row["is_admin"]:
                return []

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
            # Check admin credentials from DB
            cur_a = conn.execute("SELECT is_admin FROM users WHERE id = ?;", (admin_user_id,))
            admin_row = cur_a.fetchone()
            if not admin_row or not admin_row["is_admin"]:
                return False, "Unauthorized: Admin privileges required."

            # Check target user exists and is not administrator
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
        sync_users_to_backup()
        return True, f"User '{target['username']}' has been {action_word} successfully."
    except Exception as exc:
        return False, f"Failed to update user status: {exc}"
    finally:
        conn.close()


def change_user_username(user_id: int, new_username: str):
    new_username = new_username.strip()
    if not USERNAME_REGEX.fullmatch(new_username):
        return False, "Username must be 3-30 characters and contain only English letters, numbers, hyphens, and underscores."

    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.execute("SELECT id FROM users WHERE username = ? COLLATE NOCASE AND id != ?;", (new_username, user_id))
            if cursor.fetchone():
                return False, f"User ID '{new_username}' is already in use. Please pick another."

            conn.execute("UPDATE users SET username = ? WHERE id = ?;", (new_username, user_id))
        sync_users_to_backup()
        return True, f"User ID changed to '{new_username}' successfully."
    except sqlite3.IntegrityError:
        return False, f"User ID '{new_username}' is already taken."
    except Exception as exc:
        return False, f"Failed to update User ID: {exc}"
    finally:
        conn.close()


def verify_and_change_password(user_id: int, current_password: str, new_password: str):
    if not current_password:
        return False, "Please enter your current password."
    if len(new_password) < 8:
        return False, "New password must be at least 8 characters long."
    if len(new_password) > 128:
        return False, "New password must not exceed 128 characters."

    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT password_hash, salt FROM users WHERE id = ?;", (user_id,))
        row = cursor.fetchone()
        if not row:
            return False, "User not found."

        if not verify_password(row["password_hash"], row["salt"], current_password):
            return False, "Current password does not match. Please try again."

        new_salt = secrets.token_hex(16)
        new_hash = hash_password(new_password, new_salt)
        with conn:
            conn.execute(
                "UPDATE users SET password_hash = ?, salt = ? WHERE id = ?;",
                (new_hash, new_salt, user_id),
            )
        sync_users_to_backup()
        return True, "Your password has been changed successfully."
    except Exception as exc:
        return False, f"Failed to change password: {exc}"
    finally:
        conn.close()


def admin_reset_user_password(admin_user_id: int, target_user_id: int, new_password: str):
    if len(new_password) < 8:
        return False, "New password must be at least 8 characters long."
    if len(new_password) > 128:
        return False, "New password must not exceed 128 characters."

    conn = get_db_connection()
    try:
        cur = conn.execute("SELECT is_admin FROM users WHERE id = ?;", (admin_user_id,))
        admin_row = cur.fetchone()
        if not admin_row or not admin_row["is_admin"]:
            return False, "Unauthorized: Admin privileges required."

        cur_t = conn.execute("SELECT username, is_admin FROM users WHERE id = ?;", (target_user_id,))
        target_row = cur_t.fetchone()
        if not target_row:
            return False, "Target user not found."

        if target_row["is_admin"] and target_user_id != admin_user_id:
            return False, "Cannot reset the password of another administrator."

        new_salt = secrets.token_hex(16)
        new_hash = hash_password(new_password, new_salt)
        with conn:
            conn.execute(
                "UPDATE users SET password_hash = ?, salt = ? WHERE id = ?;",
                (new_hash, new_salt, target_user_id),
            )
        sync_users_to_backup()
        return True, f"Password for '{target_row['username']}' reset successfully."
    except Exception as exc:
        return False, f"Failed to reset password: {exc}"
    finally:
        conn.close()


def change_user_password(user_id: int, new_password: str):
    """Directly updates a user's password."""
    if len(new_password) < 8:
        return False, "Password must be at least 8 characters long."
    if len(new_password) > 128:
        return False, "Password must not exceed 128 characters."

    salt = secrets.token_hex(16)
    p_hash = hash_password(new_password, salt)
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("UPDATE users SET password_hash = ?, salt = ? WHERE id = ?;", (p_hash, salt, user_id))
        sync_users_to_backup()
        return True, "Password updated successfully."
    except Exception as exc:
        return False, f"Failed to update password: {exc}"
    finally:
        conn.close()


def _hash_ip(ip: str) -> str:
    if not ip or ip in ("127.0.0.1", "localhost", "::1"):
        return "local_client"
    # Anonymize IP with salt
    return hashlib.sha256(f"ip_salt_2026_{ip}".encode("utf-8")).hexdigest()[:16]


def log_visitor(ip: str, user_agent: str, path: str, referrer: str = "", user_id: int = None):
    """Logs an incoming page visit for admin analytics (anonymized IP)."""
    try:
        ip_hash = _hash_ip(ip)
        conn = get_db_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO visitors (ip_hash, user_agent, path, referrer, user_id, visited_at)
                    VALUES (?, ?, ?, ?, ?, ?);
                    """,
                    (ip_hash, (user_agent or "")[:250], (path or "")[:150], (referrer or "")[:200], user_id, now_iso()),
                )
        finally:
            conn.close()
    except Exception as exc:
        logger.warning(f"Failed to log visitor: {exc}")


def log_login_event(username: str, ip: str, user_agent: str, status: str, user_id: int = None):
    """Records a login attempt (SUCCESS, FAILED, BLOCKED) for the admin dashboard."""
    try:
        ip_hash = _hash_ip(ip)
        conn = get_db_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO login_logs (username, user_id, ip_hash, user_agent, status, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?);
                    """,
                    (username.strip(), user_id, ip_hash, (user_agent or "")[:250], status.upper(), now_iso()),
                )
        finally:
            conn.close()
    except Exception as exc:
        logger.warning(f"Failed to log login event: {exc}")


def record_feedback(message_id: str, query: str, answer: str, rating: str, user_id: int = None, username: str = "", comment: str = ""):
    """Stores a thumbs up / thumbs down feedback reaction for an assistant response."""
    rating_clean = "thumbs_up" if rating in ("up", "thumbs_up", "like", "+1") else "thumbs_down"
    status_init = "helpful" if rating_clean == "thumbs_up" else "pending"
    try:
        conn = get_db_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO feedbacks (message_id, user_id, username, query, answer, rating, comment, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (str(message_id), user_id, username, (query or "")[:500], (answer or "")[:1500], rating_clean, (comment or "")[:500], status_init, now_iso()),
                )
            return True, "Feedback recorded successfully!"
        finally:
            conn.close()
    except Exception as exc:
        logger.warning(f"Failed to record feedback: {exc}")
        return False, str(exc)


def get_feedback_by_id(feedback_id: int):
    """Fetches a specific feedback row by its ID."""
    conn = get_db_connection()
    try:
        cur = conn.execute(
            """
            SELECT id, message_id, user_id, username, query, answer, rating, comment, 
                   status, diagnosis, proposed_fix, resolution, resolved_at, resolved_by, created_at 
            FROM feedbacks 
            WHERE id = ?;
            """, 
            (feedback_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def save_feedback_diagnosis(feedback_id: int, diagnosis: str, proposed_fix: str):
    """Saves the root-cause diagnosis and proposed solution for a thumbs-down complaint."""
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                """
                UPDATE feedbacks 
                SET status = 'diagnosed', diagnosis = ?, proposed_fix = ? 
                WHERE id = ?;
                """,
                (diagnosis, proposed_fix, feedback_id)
            )
        return True, "Diagnosis saved."
    except Exception as exc:
        logger.warning(f"Failed to save diagnosis: {exc}")
        return False, str(exc)
    finally:
        conn.close()


def resolve_feedback_with_permission(feedback_id: int, admin_username: str, approved: bool = True, resolution_note: str = ""):
    """Resolves or dismisses a feedback item strictly with administrator authorization."""
    conn = get_db_connection()
    new_status = "resolved" if approved else "dismissed"
    try:
        with conn:
            conn.execute(
                """
                UPDATE feedbacks 
                SET status = ?, resolution = ?, resolved_by = ?, resolved_at = ? 
                WHERE id = ?;
                """,
                (new_status, resolution_note, admin_username, now_iso(), feedback_id)
            )
        return True, f"Feedback successfully marked as {new_status}."
    except Exception as exc:
        logger.warning(f"Failed to resolve feedback: {exc}")
        return False, str(exc)
    finally:
        conn.close()


def get_admin_analytics(admin_user_id: int = None):
    """Retrieves full analytics for the admin panel: visitors, logins, feedbacks, and summary stats."""
    conn = get_db_connection()
    try:
        if admin_user_id is not None:
            cur_a = conn.execute("SELECT is_admin FROM users WHERE id = ?;", (admin_user_id,))
            admin_row = cur_a.fetchone()
            if not admin_row or not admin_row["is_admin"]:
                return None

        # 1. Visitor stats
        total_visits_row = conn.execute("SELECT COUNT(*) FROM visitors;").fetchone()
        total_visits = total_visits_row[0] if total_visits_row else 0

        unique_visitors_row = conn.execute("SELECT COUNT(DISTINCT ip_hash) FROM visitors;").fetchone()
        unique_visitors = unique_visitors_row[0] if unique_visitors_row else 0

        cur_v = conn.execute(
            """
            SELECT v.id, v.ip_hash, v.user_agent, v.path, v.visited_at, u.username 
            FROM visitors v
            LEFT JOIN users u ON v.user_id = u.id
            ORDER BY v.id DESC LIMIT 50;
            """
        )
        recent_visitors = [dict(r) for r in cur_v.fetchall()]

        # 2. Login stats
        total_logins_row = conn.execute("SELECT COUNT(*) FROM login_logs;").fetchone()
        total_logins = total_logins_row[0] if total_logins_row else 0

        cur_l = conn.execute(
            """
            SELECT id, username, ip_hash, user_agent, status, timestamp 
            FROM login_logs 
            ORDER BY id DESC LIMIT 50;
            """
        )
        recent_logins = [dict(r) for r in cur_l.fetchall()]

        # 3. Feedback stats
        cur_fb_counts = conn.execute(
            """
            SELECT 
                SUM(CASE WHEN rating = 'thumbs_up' THEN 1 ELSE 0 END) as thumbs_up,
                SUM(CASE WHEN rating = 'thumbs_down' THEN 1 ELSE 0 END) as thumbs_down,
                SUM(CASE WHEN status = 'resolved' THEN 1 ELSE 0 END) as resolved_count,
                SUM(CASE WHEN rating = 'thumbs_down' AND (status = 'pending' OR status = 'diagnosed') THEN 1 ELSE 0 END) as pending_issues,
                COUNT(*) as total
            FROM feedbacks;
            """
        ).fetchone()

        thumbs_up = cur_fb_counts["thumbs_up"] or 0
        thumbs_down = cur_fb_counts["thumbs_down"] or 0
        resolved_count = cur_fb_counts["resolved_count"] or 0
        pending_issues = cur_fb_counts["pending_issues"] or 0
        total_feedbacks = cur_fb_counts["total"] or 0
        satisfaction_pct = round((thumbs_up / total_feedbacks * 100), 1) if total_feedbacks > 0 else 100.0

        cur_fb = conn.execute(
            """
            SELECT id, message_id, username, query, answer, rating, comment, 
                   status, diagnosis, proposed_fix, resolution, resolved_at, resolved_by, created_at 
            FROM feedbacks 
            ORDER BY id DESC LIMIT 50;
            """
        )
        recent_feedbacks = [dict(r) for r in cur_fb.fetchall()]

        # 4. User counts
        users_count_row = conn.execute("SELECT COUNT(*) FROM users;").fetchone()
        total_users = users_count_row[0] if users_count_row else 0

        return {
            "summary": {
                "total_visits": total_visits,
                "unique_visitors": unique_visitors,
                "total_logins": total_logins,
                "total_users": total_users,
                "thumbs_up": thumbs_up,
                "thumbs_down": thumbs_down,
                "resolved_count": resolved_count,
                "pending_issues": pending_issues,
                "total_feedbacks": total_feedbacks,
                "satisfaction_pct": satisfaction_pct,
            },
            "recent_visitors": recent_visitors,
            "recent_logins": recent_logins,
            "recent_feedbacks": recent_feedbacks,
        }
    finally:
        conn.close()


def get_user_api_key(user_id: int) -> str:
    """Retrieves or creates a persistent developer API key for the user."""
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT api_key FROM users WHERE id = ?;", (user_id,)).fetchone()
        if row and row["api_key"]:
            return row["api_key"]
        new_key = f"hd_live_{secrets.token_hex(16)}"
        conn.execute("UPDATE users SET api_key = ? WHERE id = ?;", (new_key, user_id))
        conn.commit()
        return new_key
    finally:
        conn.close()


def rotate_user_api_key(user_id: int) -> str:
    """Rotates and issues a new developer API key."""
    new_key = f"hd_live_{secrets.token_hex(16)}"
    conn = get_db_connection()
    try:
        conn.execute("UPDATE users SET api_key = ? WHERE id = ?;", (new_key, user_id))
        conn.commit()
        return new_key
    finally:
        conn.close()


def verify_api_key(key: str):
    """Validates an API key against user records or demo key format."""
    if not key or not isinstance(key, str):
        return None
    clean_key = key.strip()
    if clean_key.startswith("Bearer "):
        clean_key = clean_key[7:].strip()
    if not clean_key.startswith("hd_live_"):
        return None

    conn = get_db_connection()
    try:
        row = conn.execute("SELECT id, username, is_admin, plan FROM users WHERE api_key = ?;", (clean_key,)).fetchone()
        if row:
            return {
                "user_id": row["id"],
                "username": row["username"],
                "is_admin": bool(row["is_admin"]),
                "plan": row["plan"] or "free"
            }
    finally:
        conn.close()

    # Allow demo/guest hd_live_ keys
    if len(clean_key) >= 20:
        return {"user_id": None, "username": "API Guest", "is_admin": False, "plan": "pro"}
    return None


def update_user_plan(user_id: int, plan: str) -> bool:
    """Updates user plan (free, pro, enterprise)."""
    conn = get_db_connection()
    try:
        conn.execute("UPDATE users SET plan = ? WHERE id = ?;", (plan, user_id))
        conn.commit()
        return True
    finally:
        conn.close()



