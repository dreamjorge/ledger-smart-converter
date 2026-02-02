import os
import pandas as pd
import joblib
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

MODEL_DIR = Path("config/ml_models")
MODEL_PATH = MODEL_DIR / "categorizer_v1.joblib"

class TransactionCategorizer:
    def __init__(self):
        self.pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(ngram_range=(1, 2), max_features=1000)),
            ('clf', LogisticRegression(max_iter=1000))
        ])
        self.is_trained = False
        self.classes_ = []

    def train_from_csvs(self, csv_paths: List[Path]):
        """
        Loads data from multiple Firefly CSVs and trains the model.
        Expects columns: 'description', 'destination_name'
        """
        dfs = []
        for p in csv_paths:
            if p.exists():
                try:
                    df = pd.read_csv(p)
                    # We only train on withdrawals (cargos) because transfers (abonos) 
                    # usually have very generic descriptions.
                    if 'type' in df.columns:
                        df = df[df['type'] == 'withdrawal']
                    
                    if 'description' in df.columns and 'destination_name' in df.columns:
                        dfs.append(df[['description', 'destination_name']])
                except Exception as e:
                    print(f"Error loading {p}: {e}")
        
        if not dfs:
            return False
        
        data = pd.concat(dfs).dropna()
        # Clean Uncategorized ones from training if possible, or keep them if that's all we have
        # data = data[~data['destination_name'].str.contains('Uncategorized', na=False)]
        
        if len(data) < 5: # Minimum data threshold
            return False

        X = data['description']
        y = data['destination_name']
        
        self.pipeline.fit(X, y)
        self.classes_ = self.pipeline.named_steps['clf'].classes_.tolist()
        self.is_trained = True
        return True

    def save_model(self):
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump({
            'pipeline': self.pipeline,
            'is_trained': self.is_trained,
            'classes': self.classes_
        }, MODEL_PATH)

    def load_model(self):
        if MODEL_PATH.exists():
            data = joblib.load(MODEL_PATH)
            self.pipeline = data['pipeline']
            self.is_trained = data['is_trained']
            self.classes_ = data['classes']
            return True
        return False

    def predict(self, description: str) -> List[Tuple[str, float]]:
        """
        Returns a list of (category, probability) pairs sorted by confidence.
        """
        if not self.is_trained:
            return []
        
        probas = self.pipeline.predict_proba([description])[0]
        results = zip(self.classes_, probas)
        sorted_results = sorted(results, key=lambda x: x[1], reverse=True)
        
        return [(cat, float(prob)) for cat, prob in sorted_results if prob > 0.1]

# Utility to train the model on all available data
def train_global_model():
    engine = TransactionCategorizer()
    data_dir = Path("data")
    csv_files = list(data_dir.glob("**/*.csv"))
    # Filter only firefly import csvs
    import_csvs = [f for f in csv_files if "firefly" in f.name]
    
    if engine.train_from_csvs(import_csvs):
        engine.save_model()
        return f"Model trained with {len(import_csvs)} files."
    return "Not enough data to train model."

if __name__ == "__main__":
    status = train_global_model()
    print(status)
