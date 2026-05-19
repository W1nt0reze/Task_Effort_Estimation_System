from __future__ import annotations

import sys

from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.team_rules import known_teams  # noqa: E402
from src.train_model import FEATURE_COLUMNS, train_and_save  # noqa: E402

AUTO_RETRAIN_EVERY_N_NEW_TASKS = 50

BASE_DATASET = REPO_ROOT / "data" / "processed" / "dataset_filtered_resolved.csv"
MERGED_DATASET = REPO_ROOT / "data" / "processed" / "dataset_merged.csv"
MODEL_PATH = REPO_ROOT / "models" / "effort_model.joblib"

_model_cache: dict | None = None


def normalize_team(team: str | None) -> str:
    value = (team or "").strip().lower()
    return value or "other"


def load_meta_from_csv() -> tuple[list[str], list[str], list[str]]:
    if not BASE_DATASET.is_file():
        raise FileNotFoundError(
            f"Dataset not found: {BASE_DATASET}. Run src/preprocess.py first."
        )

    df = pd.read_csv(BASE_DATASET, usecols=["type", "team"])

    priorities = [
        "Низкий",
        "Средний",
        "Высокий",
        "Критический",
    ]

    types = sorted(df["type"].dropna().astype(str).unique().tolist())
    dataset_teams = set(df["team"].dropna().astype(str))

    teams = [team for team in known_teams() if team in dataset_teams]
    extras = sorted(dataset_teams - set(teams))

    return priorities, types, teams + extras


def _get_model_pack() -> dict:
    global _model_cache

    if _model_cache is None:
        if not MODEL_PATH.is_file():
            raise FileNotFoundError(
                f"Model not found: {MODEL_PATH}. Run src/train_model.py first."
            )
        _model_cache = joblib.load(MODEL_PATH)

    return _model_cache


def invalidate_model_cache() -> None:
    global _model_cache
    _model_cache = None


def _make_feature_row(
    priority: str,
    type: str,
    team: str,
    story_points: float,
    ref: datetime,
) -> dict:
    return {
        "story_points": float(story_points),
        "priority": priority,
        "type": type,
        "team": normalize_team(team),
        "created_dow": ref.weekday(),
        "created_month": ref.month,
    }


def predict_hours(
    priority: str,
    type: str,
    team: str,
    story_points: float,
    ref: datetime | None = None,
) -> float:
    pack = _get_model_pack()
    model = pack["model"]
    use_log = bool(pack.get("log", False))

    ref = ref or datetime.now()
    row = _make_feature_row(priority, type, team, story_points, ref)
    X = pd.DataFrame([row], columns=FEATURE_COLUMNS)

    pred = float(model.predict(X)[0])
    if use_log:
        pred = float(np.expm1(pred))

    return max(0.0, pred)


def task_rows_to_training_frame(rows: list) -> pd.DataFrame:
    out_rows = []

    for r in rows:
        created = datetime.fromisoformat(r.created_at)
        out_rows.append(
            {
                "story_points": float(r.story_points),
                "priority": r.priority,
                "type": r.type,
                "team": normalize_team(r.team),
                "created_dow": created.weekday(),
                "created_month": created.month,
                "target_hours": float(r.actual_hours),
            }
        )

    return pd.DataFrame(out_rows)


def merge_and_retrain() -> dict:
    if not BASE_DATASET.is_file():
        raise FileNotFoundError(
            f"Dataset not found: {BASE_DATASET}. Run src/preprocess.py first."
        )

    base = pd.read_csv(BASE_DATASET)

    from app.database import fetch_all_tasks

    user_df = task_rows_to_training_frame(fetch_all_tasks())
    merged = pd.concat([base, user_df], ignore_index=True) if len(user_df) else base

    MERGED_DATASET.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(MERGED_DATASET, index=False)

    summary = train_and_save(MERGED_DATASET, MODEL_PATH)
    invalidate_model_cache()
    summary["merged_path"] = str(MERGED_DATASET)

    return summary
