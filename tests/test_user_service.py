import sqlite3

from services.db_service import DatabaseService
from services import user_service


def test_create_user_hashes_password_and_verifies_it(tmp_path, monkeypatch):
    db = DatabaseService(db_path=tmp_path / "ledger.db")
    db.initialize()
    monkeypatch.setattr(user_service, "_PREFS_PATH", tmp_path / "prefs.json")

    created = user_service.create_user(
        db,
        user_id="maria",
        display_name="Maria",
        password="1234",
    )
    row = user_service.get_user(db, "maria")

    assert created is True
    assert row["password_hash"] is not None
    assert row["password_hash"] != "1234"
    assert user_service.verify_password(db, "maria", "1234") is True
    assert user_service.verify_password(db, "maria", "9999") is False


def test_verify_password_allows_open_profiles(tmp_path, monkeypatch):
    db = DatabaseService(db_path=tmp_path / "ledger.db")
    db.initialize()
    monkeypatch.setattr(user_service, "_PREFS_PATH", tmp_path / "prefs.json")

    assert user_service.create_user(db, "shared", "Shared") is True
    assert user_service.verify_password(db, "shared", "") is True


def test_set_password_can_add_and_clear_pin(tmp_path, monkeypatch):
    db = DatabaseService(db_path=tmp_path / "ledger.db")
    db.initialize()
    monkeypatch.setattr(user_service, "_PREFS_PATH", tmp_path / "prefs.json")
    user_service.create_user(db, "juan", "Juan")

    assert user_service.set_password(db, "juan", "4321") is True
    assert user_service.verify_password(db, "juan", "4321") is True
    assert user_service.set_password(db, "juan", None) is True
    assert user_service.get_user(db, "juan")["password_hash"] is None
    assert user_service.verify_password(db, "juan", "") is True


def test_list_users_migrates_old_schema_without_password_hash(tmp_path, monkeypatch):
    db_path = tmp_path / "legacy.db"
    monkeypatch.setattr(user_service, "_PREFS_PATH", tmp_path / "prefs.json")

    con = sqlite3.connect(db_path)
    con.execute(
        """
        CREATE TABLE users (
            user_id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            color TEXT NOT NULL DEFAULT '#4fc3f7',
            is_admin INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    con.execute(
        "INSERT INTO users (user_id, display_name, color, is_admin) VALUES ('ana', 'Ana', '#ffffff', 0)"
    )
    con.commit()
    con.close()

    db = DatabaseService(db_path=db_path)
    users = user_service.list_users(db)
    columns = {row["name"] for row in db.fetch_all("PRAGMA table_info(users)")}

    assert users[0]["user_id"] == "ana"
    assert users[0]["password_hash"] is None
    assert "password_hash" in columns


# ---------------------------------------------------------------------------
# Preferences
# ---------------------------------------------------------------------------


def test_load_prefs_returns_empty_dict_when_file_missing(tmp_path, monkeypatch):
    """When prefs.json does not exist, _load_prefs returns empty dict."""
    monkeypatch.setattr(user_service, "_PREFS_PATH", tmp_path / "prefs.json")
    assert user_service._load_prefs() == {}


def test_load_prefs_returns_empty_dict_on_corrupt_json(tmp_path, monkeypatch):
    """When prefs.json contains invalid JSON, _load_prefs returns empty dict."""
    corrupt_file = tmp_path / "prefs.json"
    corrupt_file.write_text("{invalid json", encoding="utf-8")
    monkeypatch.setattr(user_service, "_PREFS_PATH", corrupt_file)
    assert user_service._load_prefs() == {}


def test_get_pref_returns_default_when_key_missing(tmp_path, monkeypatch):
    """get_pref returns the default value when the key does not exist."""
    monkeypatch.setattr(user_service, "_PREFS_PATH", tmp_path / "prefs.json")
    assert user_service.get_pref("missing_key", default="fallback") == "fallback"


def test_get_pref_returns_stored_value(tmp_path, monkeypatch):
    """get_pref returns the stored value when the key exists."""
    monkeypatch.setattr(user_service, "_PREFS_PATH", tmp_path / "prefs.json")
    user_service.set_pref("theme", "dark")
    assert user_service.get_pref("theme") == "dark"


def test_set_pref_updates_existing_key(tmp_path, monkeypatch):
    """set_pref updates an existing preference key."""
    monkeypatch.setattr(user_service, "_PREFS_PATH", tmp_path / "prefs.json")
    user_service.set_pref("lang", "es")
    user_service.set_pref("lang", "en")
    assert user_service.get_pref("lang") == "en"


def test_set_active_user_clears_with_none(tmp_path, monkeypatch):
    """set_active_user(None) removes active_user from prefs.json."""
    monkeypatch.setattr(user_service, "_PREFS_PATH", tmp_path / "prefs.json")
    user_service.set_active_user("juan")
    user_service.set_active_user(None)
    assert user_service.get_active_user() is None


def test_set_active_user_stores_user_id(tmp_path, monkeypatch):
    """set_active_user stores the user_id in prefs.json."""
    monkeypatch.setattr(user_service, "_PREFS_PATH", tmp_path / "prefs.json")
    user_service.set_active_user("maria")
    assert user_service.get_active_user() == "maria"


# ---------------------------------------------------------------------------
# User CRUD edge cases
# ---------------------------------------------------------------------------


def test_create_user_rejects_empty_user_id(tmp_path, monkeypatch):
    """create_user returns False when user_id is empty or whitespace."""
    db = DatabaseService(db_path=tmp_path / "ledger.db")
    db.initialize()
    monkeypatch.setattr(user_service, "_PREFS_PATH", tmp_path / "prefs.json")
    assert user_service.create_user(db, "", "DisplayName") is False
    assert user_service.create_user(db, "   ", "DisplayName") is False


def test_create_user_rejects_empty_display_name(tmp_path, monkeypatch):
    """create_user returns False when display_name is empty or whitespace."""
    db = DatabaseService(db_path=tmp_path / "ledger.db")
    db.initialize()
    monkeypatch.setattr(user_service, "_PREFS_PATH", tmp_path / "prefs.json")
    assert user_service.create_user(db, "validid", "") is False
    assert user_service.create_user(db, "validid", "   ") is False


def test_create_user_rejects_duplicate_user_id(tmp_path, monkeypatch):
    """create_user returns False when user_id already exists."""
    db = DatabaseService(db_path=tmp_path / "ledger.db")
    db.initialize()
    monkeypatch.setattr(user_service, "_PREFS_PATH", tmp_path / "prefs.json")
    user_service.create_user(db, "juan", "Juan")
    assert user_service.create_user(db, "juan", "Juan 2") is False


def test_verify_password_returns_false_for_unknown_user(tmp_path, monkeypatch):
    """verify_password returns False when user does not exist."""
    db = DatabaseService(db_path=tmp_path / "ledger.db")
    db.initialize()
    monkeypatch.setattr(user_service, "_PREFS_PATH", tmp_path / "prefs.json")
    assert user_service.verify_password(db, "nobody", "anypass") is False


def test_set_password_returns_false_for_unknown_user(tmp_path, monkeypatch):
    """set_password returns False when user does not exist."""
    db = DatabaseService(db_path=tmp_path / "ledger.db")
    db.initialize()
    monkeypatch.setattr(user_service, "_PREFS_PATH", tmp_path / "prefs.json")
    assert user_service.set_password(db, "ghost", "anypass") is False


def test_check_password_returns_false_on_invalid_hash(tmp_path, monkeypatch):
    """_check_password returns False when bcrypt raises an exception on invalid hash."""
    import bcrypt

    monkeypatch.setattr(
        bcrypt,
        "checkpw",
        lambda *a, **k: (_ for _ in ()).throw(OSError("invalid hash")),
    )
    result = user_service._check_password("anypass", "bad_hash_format")
    assert result is False


def test_ensure_users_columns_logs_warning_on_alter_failure(
    tmp_path, monkeypatch, caplog
):
    """_ensure_users_columns logs warning when ALTER TABLE fails."""
    import logging

    db = DatabaseService(db_path=tmp_path / "ledger.db")
    db.initialize()
    monkeypatch.setattr(user_service, "_PREFS_PATH", tmp_path / "prefs.json")

    # Create users table WITHOUT password_hash column
    db.fetch_one(
        "CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, display_name TEXT)"
    )
    # Mock the ALTER to fail
    original_fetch = db.fetch_one
    call_count = [0]

    def failing_fetch(sql, *args, **kwargs):
        if "password_hash" in sql:
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("mocked alter failure")
        return original_fetch(sql, *args, **kwargs)

    monkeypatch.setattr(db, "fetch_one", failing_fetch)
    with caplog.at_level(logging.WARNING):
        user_service._ensure_users_columns(db)
    assert any(
        "Could not add password_hash column" in r.message for r in caplog.records
    )


def test_delete_user_clears_active_user(tmp_path, monkeypatch):
    """delete_user clears active_user if it matches the deleted user."""
    db = DatabaseService(db_path=tmp_path / "ledger.db")
    db.initialize()
    monkeypatch.setattr(user_service, "_PREFS_PATH", tmp_path / "prefs.json")
    user_service.create_user(db, "juan", "Juan")
    user_service.set_active_user("juan")
    assert user_service.get_active_user() == "juan"
    user_service.delete_user(db, "juan")
    assert user_service.get_active_user() is None
