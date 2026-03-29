"""User service: lightweight local family profiles with optional PIN protection.

Active user and language preference are persisted to config/prefs.json.
Passwords are stored as bcrypt hashes; a NULL hash means no PIN required.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_PREFS_PATH: Optional[Path] = None


def _prefs_path() -> Path:
    global _PREFS_PATH
    if _PREFS_PATH is None:
        from settings import load_settings
        _PREFS_PATH = load_settings().config_dir / "prefs.json"
    return _PREFS_PATH


def _load_prefs() -> Dict:
    path = _prefs_path()
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_prefs(prefs: Dict) -> None:
    path = _prefs_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(prefs, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Preferences (language + active user)
# ---------------------------------------------------------------------------

def get_pref(key: str, default=None):
    """Read a single preference value from prefs.json."""
    return _load_prefs().get(key, default)


def set_pref(key: str, value) -> None:
    """Write a single preference value to prefs.json."""
    prefs = _load_prefs()
    prefs[key] = value
    _save_prefs(prefs)


def get_active_user() -> Optional[str]:
    """Return the currently active user_id from prefs.json, or None."""
    return _load_prefs().get("active_user")


def set_active_user(user_id: Optional[str]) -> None:
    """Persist the active user_id to prefs.json."""
    prefs = _load_prefs()
    if user_id is None:
        prefs.pop("active_user", None)
    else:
        prefs["active_user"] = user_id
    _save_prefs(prefs)


# ---------------------------------------------------------------------------
# User CRUD
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Password helpers (bcrypt)
# ---------------------------------------------------------------------------

def _hash_password(password: str) -> str:
    """Return a bcrypt hash string for *password*."""
    import bcrypt
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _check_password(password: str, hashed: str) -> bool:
    """Return True if *password* matches the bcrypt *hashed* string."""
    import bcrypt
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False


# ---------------------------------------------------------------------------
# User CRUD
# ---------------------------------------------------------------------------

def _ensure_users_columns(db) -> None:
    """Add password_hash column to users table if it doesn't exist yet."""
    try:
        db.fetch_one("SELECT password_hash FROM users LIMIT 1")
    except Exception:
        try:
            db.fetch_one("ALTER TABLE users ADD COLUMN password_hash TEXT")
            logger.info("Migrated users table: added password_hash column")
        except Exception as exc:
            logger.warning("Could not add password_hash column: %s", exc)


def list_users(db) -> List[Dict]:
    """Return all users ordered by display_name."""
    _ensure_users_columns(db)
    rows = db.fetch_all(
        "SELECT user_id, display_name, color, is_admin, created_at, password_hash FROM users ORDER BY display_name"
    )
    return [dict(r) for r in rows] if rows else []


def get_user(db, user_id: str) -> Optional[Dict]:
    """Return a single user dict or None."""
    _ensure_users_columns(db)
    row = db.fetch_one(
        "SELECT user_id, display_name, color, is_admin, created_at, password_hash FROM users WHERE user_id = ?",
        (user_id,),
    )
    return dict(row) if row else None


def create_user(
    db,
    user_id: str,
    display_name: str,
    color: str = "#4fc3f7",
    is_admin: bool = False,
    password: Optional[str] = None,
) -> bool:
    """Insert a new user. Returns True on success, False if user_id already exists.

    If *password* is provided (non-empty string), it is hashed with bcrypt and
    stored in password_hash. A NULL hash means no PIN is required to switch.
    """
    _ensure_users_columns(db)
    user_id = user_id.strip().lower()
    if not user_id or not display_name.strip():
        return False
    if get_user(db, user_id):
        return False
    now = datetime.now(timezone.utc).isoformat()
    password_hash = _hash_password(password) if password else None
    db.fetch_one(
        "INSERT INTO users (user_id, display_name, color, is_admin, password_hash, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, display_name.strip(), color, int(is_admin), password_hash, now),
    )
    logger.info("Created user %r (%s)", user_id, display_name)
    return True


def verify_password(db, user_id: str, password: str) -> bool:
    """Return True if *password* matches the stored hash for *user_id*.

    Returns True if the user has no password set (NULL hash) — treated as open.
    Returns False if the user doesn't exist.
    """
    user = get_user(db, user_id)
    if user is None:
        return False
    stored_hash = user.get("password_hash")
    if stored_hash is None:
        return True  # No PIN required
    return _check_password(password, stored_hash)


def set_password(db, user_id: str, password: Optional[str]) -> bool:
    """Set or clear the password for *user_id*.

    Pass *password=None* to remove the PIN (allow open switching).
    Returns False if the user doesn't exist.
    """
    if get_user(db, user_id) is None:
        return False
    hashed = _hash_password(password) if password else None
    db.fetch_one("UPDATE users SET password_hash = ? WHERE user_id = ?", (hashed, user_id))
    return True


def delete_user(db, user_id: str) -> bool:
    """Delete a user. Transactions tagged with this user become unassigned (user_id = NULL)."""
    db.fetch_one("UPDATE transactions SET user_id = NULL WHERE user_id = ?", (user_id,))
    db.fetch_one("DELETE FROM users WHERE user_id = ?", (user_id,))
    # If this was the active user, clear the preference
    if get_active_user() == user_id:
        set_active_user(None)
    return True
