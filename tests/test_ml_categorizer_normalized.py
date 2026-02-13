from pathlib import Path

import pandas as pd

import ml_categorizer as ml


def test_train_prefers_normalized_description_when_available(tmp_path, monkeypatch):
    csv_path = tmp_path / "train_firefly.csv"
    pd.DataFrame(
        [
            {"type": "withdrawal", "description": "RAW A", "normalized_description": "NORMAL A", "destination_name": "Expenses:A"},
            {"type": "withdrawal", "description": "RAW B", "normalized_description": "NORMAL B", "destination_name": "Expenses:B"},
            {"type": "withdrawal", "description": "RAW C", "normalized_description": "NORMAL C", "destination_name": "Expenses:C"},
            {"type": "withdrawal", "description": "RAW D", "normalized_description": "NORMAL D", "destination_name": "Expenses:D"},
            {"type": "withdrawal", "description": "RAW E", "normalized_description": "NORMAL E", "destination_name": "Expenses:E"},
        ]
    ).to_csv(csv_path, index=False)

    captured = {}

    class DummyPipeline:
        def __init__(self):
            self.named_steps = {"clf": type("C", (), {"classes_": ["Expenses:A"]})()}

        def fit(self, X, y):
            captured["X"] = list(X)
            captured["y"] = list(y)
            return self

        def predict_proba(self, _x):
            return [[1.0]]

    engine = ml.TransactionCategorizer()
    monkeypatch.setattr(engine, "pipeline", DummyPipeline())
    assert engine.train_from_csvs([csv_path]) is True
    assert captured["X"][0] == "NORMAL A"


def test_predict_normalizes_input_before_model(monkeypatch):
    captured = {}

    class DummyPipeline:
        def __init__(self):
            self.named_steps = {"clf": type("C", (), {"classes_": ["Expenses:Entertainment"]})()}

        def predict_proba(self, X):
            captured["X"] = list(X)
            return [[0.9]]

    engine = ml.TransactionCategorizer()
    engine.pipeline = DummyPipeline()
    engine.is_trained = True
    engine.classes_ = ["Expenses:Entertainment"]

    preds = engine.predict("MERPAGO NETFLIX 12345")
    assert preds
    assert captured["X"][0] == "MercadoPago Netflix"
