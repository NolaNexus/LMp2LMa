"""Minimal offline training job for the FAQ intent classifier.

Trains a TF-IDF + LogisticRegression model over the FAQ corpus, logs the run
to MLflow, and writes run metadata (model URI, metrics, timestamp) to
``last_run.json`` for retraining-trigger evaluation and monitoring.
"""
from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import joblib
import mlflow
import mlflow.sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

DEFAULT_CONFIG = Path(__file__).with_name("config.json")


@dataclass
class TrainResult:
    run_id: str
    model_uri: str
    accuracy: float
    train_samples: int
    test_samples: int
    trained_at: str

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


def load_corpus(corpus_path: Path):
    docs = json.loads(Path(corpus_path).read_text())
    texts = [f"{d['question']} {d['answer']}" for d in docs]
    labels = [d.get("topic", d.get("category", "faq")) for d in docs]
    return texts, labels


def train(config_path: Optional[Path] = None) -> TrainResult:
    cfg = json.loads(Path(config_path or DEFAULT_CONFIG).read_text())
    corpus_path = Path(cfg["data"]["corpus_path"])
    if not corpus_path.exists():
        repo_root = Path(__file__).resolve().parents[2]
        corpus_path = repo_root / cfg["data"]["corpus_path"]
    texts, labels = load_corpus(corpus_path)

    mlflow_cfg = cfg["mlflow"]
    tracking_uri = mlflow_cfg.get("tracking_uri")
    if tracking_uri:
        mlflow.set_tracking_uri(tracking_uri)
    else:
        mlflow.set_tracking_uri(f"sqlite:///{tempfile.mkdtemp(prefix='mlflow_')}/mlflow.db")
    mlflow.set_experiment(mlflow_cfg["experiment"])

    min_class = min(labels.count(c) for c in set(labels))
    stratify = labels if min_class >= 2 else None
    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.2, random_state=42, stratify=stratify
    )
    with mlflow.start_run() as run:
        vec = TfidfVectorizer(max_features=cfg["model"]["tfidf_max_features"])
        Xv_train = vec.fit_transform(X_train)
        Xv_test = vec.transform(X_test)
        clf = LogisticRegression(C=cfg["model"]["logreg_C"], max_iter=1000)
        clf.fit(Xv_train, y_train)
        acc = float(accuracy_score(y_test, clf.predict(Xv_test)))
        mlflow.log_params(cfg["model"])
        mlflow.log_metric("accuracy", acc)
        with tempfile.TemporaryDirectory() as tmp:
            model_path = Path(tmp) / "faq_intent.joblib"
            joblib.dump({"vectorizer": vec, "classifier": clf}, model_path)
            mlflow.log_artifact(str(model_path), artifact_path="model")
        model_uri = f"runs:/{run.info.run_id}/model/faq_intent.joblib"

    result = TrainResult(
        run_id=run.info.run_id,
        model_uri=model_uri,
        accuracy=acc,
        train_samples=len(X_train),
        test_samples=len(X_test),
        trained_at=datetime.now(timezone.utc).isoformat(),
    )
    out_path = Path(cfg["output"]["last_run_path"])
    if not out_path.exists():
        repo_root = Path(__file__).resolve().parents[2]
        out_path = repo_root / cfg["output"]["last_run_path"]
    out_path.write_text(result.to_json())
    return result


if __name__ == "__main__":
    print(train().to_json())
