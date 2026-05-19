from __future__ import annotations

from pathlib import Path
import json

import joblib
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

REPO_ROOT = Path(__file__).resolve().parent.parent

DATA = REPO_ROOT / "data" / "processed" / "dataset_filtered_resolved.csv"
MODEL_OUT = REPO_ROOT / "models" / "effort_model.joblib"
METRICS_OUT = REPO_ROOT / "models" / "metrics.json"

FEATURE_COLUMNS = [
    "story_points",
    "priority",
    "type",
    "team",
    "created_dow",
    "created_month",
]

TARGET_COLUMN = "target_hours"
CATEGORICAL_COLUMNS = ["priority", "type", "team"]
NUMERIC_COLUMNS = ["story_points", "created_dow", "created_month"]


def build_pipeline(model) -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_COLUMNS),
            ("num", "passthrough", NUMERIC_COLUMNS),
        ]
    )

    return Pipeline([
        ("prep", preprocessor),
        ("model", model),
    ])


def _evaluate(y_true, predictions) -> dict[str, float]:
    return {
        "mae": float(mean_absolute_error(y_true, predictions)),
        "r2": float(r2_score(y_true, predictions)),
    }


def train_and_save(
    data_path: Path = DATA,
    model_out: Path = MODEL_OUT,
) -> dict:
    if not data_path.is_file():
        raise FileNotFoundError(f"Dataset not found: {data_path}")

    df = pd.read_csv(data_path)
    missing = [col for col in FEATURE_COLUMNS + [TARGET_COLUMN] if col not in df.columns]
    if missing:
        raise ValueError(f"Dataset is missing columns: {missing}")

    df = df.dropna(subset=FEATURE_COLUMNS + [TARGET_COLUMN]).copy()
    df = df[df[TARGET_COLUMN] > 0]

    X = df[FEATURE_COLUMNS]
    y = df[TARGET_COLUMN]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
    )

    baseline = build_pipeline(DummyRegressor(strategy="median"))
    baseline.fit(X_train, y_train)
    baseline_predictions = baseline.predict(X_test)
    baseline_metrics = _evaluate(y_test, baseline_predictions)

    model = build_pipeline(HistGradientBoostingRegressor(random_state=42))
    model.fit(X_train, np.log1p(y_train))
    predictions = np.expm1(model.predict(X_test))
    model_metrics = _evaluate(y_test, predictions)

    model_out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": model,
            "log": True,
            "feature_columns": FEATURE_COLUMNS,
            "categorical_columns": CATEGORICAL_COLUMNS,
            "numeric_columns": NUMERIC_COLUMNS,
            "target_column": TARGET_COLUMN,
            "best_model": "HistGradientBoostingRegressor_log_target",
        },
        model_out,
    )

    summary = {
        "best_model": "HistGradientBoostingRegressor_log_target",
        "mae": model_metrics["mae"],
        "r2": model_metrics["r2"],
        "baseline_mae": baseline_metrics["mae"],
        "baseline_r2": baseline_metrics["r2"],
        "rows": int(len(df)),
        "features": FEATURE_COLUMNS,
        "test_size": 0.2,
        "random_state": 42,
    }

    METRICS_OUT.parent.mkdir(parents=True, exist_ok=True)
    METRICS_OUT.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return summary


def main() -> None:
    summary = train_and_save()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Model saved: {MODEL_OUT}")
    print(f"Metrics saved: {METRICS_OUT}")


if __name__ == "__main__":
    main()
