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
    columns = {
        row["name"]
        for row in db.fetch_all("PRAGMA table_info(users)")
    }

    assert users[0]["user_id"] == "ana"
    assert users[0]["password_hash"] is None
    assert "password_hash" in columns
