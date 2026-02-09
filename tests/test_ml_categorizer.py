from pathlib import Path

import pandas as pd

import ml_categorizer as ml


def test_train_from_csvs_returns_false_when_no_files_exist(tmp_path):
    engine = ml.TransactionCategorizer()
    assert engine.train_from_csvs([tmp_path / "missing.csv"]) is False


def test_train_from_csvs_returns_false_when_rows_below_threshold(tmp_path):
    csv_path = tmp_path / "small_firefly.csv"
    pd.DataFrame(
        [
            {"type": "withdrawal", "description": "A", "destination_name": "Expenses:Food"},
            {"type": "withdrawal", "description": "B", "destination_name": "Expenses:Food"},
            {"type": "withdrawal", "description": "C", "destination_name": "Expenses:Food"},
            {"type": "transfer", "description": "PAGO", "destination_name": "Liabilities:CC"},
        ]
    ).to_csv(csv_path, index=False)

    engine = ml.TransactionCategorizer()
    assert engine.train_from_csvs([csv_path]) is False


def test_train_predict_save_and_load_model_roundtrip(tmp_path, monkeypatch):
    model_dir = tmp_path / "models"
    monkeypatch.setattr(ml, "MODEL_DIR", model_dir)
    monkeypatch.setattr(ml, "MODEL_PATH", model_dir / "categorizer_v1.joblib")

    csv_path = tmp_path / "train_firefly.csv"
    pd.DataFrame(
        [
            {"type": "withdrawal", "description": "OXXO ANTEA", "destination_name": "Expenses:Food:Convenience"},
            {"type": "withdrawal", "description": "OXXO JURIQUILLA", "destination_name": "Expenses:Food:Convenience"},
            {"type": "withdrawal", "description": "WALMART QRO", "destination_name": "Expenses:Food:Groceries"},
            {"type": "withdrawal", "description": "WAL MART ANTEA", "destination_name": "Expenses:Food:Groceries"},
            {"type": "withdrawal", "description": "NETFLIX", "destination_name": "Expenses:Entertainment:Subscriptions"},
            {"type": "withdrawal", "description": "SPOTIFY", "destination_name": "Expenses:Entertainment:Subscriptions"},
        ]
    ).to_csv(csv_path, index=False)

    engine = ml.TransactionCategorizer()
    assert engine.train_from_csvs([csv_path]) is True
    assert engine.is_trained is True
    assert len(engine.classes_) >= 2

    preds = engine.predict("WALMART EXPRESS")
    assert isinstance(preds, list)
    assert preds
    assert all(isinstance(cat, str) for cat, _ in preds)
    assert all(isinstance(prob, float) for _, prob in preds)

    engine.save_model()
    assert ml.MODEL_PATH.exists()

    loaded = ml.TransactionCategorizer()
    assert loaded.load_model() is True
    assert loaded.is_trained is True
    assert loaded.classes_


def test_predict_returns_empty_for_untrained_model():
    engine = ml.TransactionCategorizer()
    assert engine.predict("ANY MERCHANT") == []


def test_load_model_returns_false_when_model_missing(tmp_path, monkeypatch):
    model_dir = tmp_path / "models"
    monkeypatch.setattr(ml, "MODEL_DIR", model_dir)
    monkeypatch.setattr(ml, "MODEL_PATH", model_dir / "categorizer_v1.joblib")
    engine = ml.TransactionCategorizer()
    assert engine.load_model() is False


def test_train_global_model_success_and_failure(monkeypatch, tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    firefly = data_dir / "bank_firefly.csv"
    firefly.write_text("description,destination_name\nA,Expenses:X\n", encoding="utf-8")
    other = data_dir / "other.csv"
    other.write_text("x\n1\n", encoding="utf-8")

    real_path = ml.Path
    monkeypatch.setattr(ml, "Path", lambda p: data_dir if p == "data" else real_path(p))

    class DummySuccess:
        def __init__(self):
            self.saved = False

        def train_from_csvs(self, csvs):
            assert len(csvs) == 1
            assert "firefly" in csvs[0].name
            return True

        def save_model(self):
            self.saved = True

    class DummyFail:
        def train_from_csvs(self, _csvs):
            return False

        def save_model(self):
            raise AssertionError("should not be called")

    monkeypatch.setattr(ml, "TransactionCategorizer", DummySuccess)
    msg = ml.train_global_model()
    assert msg == "Model trained with 1 files."

    monkeypatch.setattr(ml, "TransactionCategorizer", DummyFail)
    msg = ml.train_global_model()
    assert msg == "Not enough data to train model."
