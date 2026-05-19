from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.team_rules import extract_team

REPO_ROOT = Path(__file__).resolve().parent.parent

RAW_TASKS = REPO_ROOT / "data" / "raw" / "tasks.xlsx"
RAW_FLOW = REPO_ROOT / "data" / "raw" / "flow_metrics.csv"
OUT_FILE = REPO_ROOT / "data" / "processed" / "dataset_filtered_resolved.csv"

REQUIRED_TASK_COLUMNS = {
    "Приоритет",
    "Тип",
    "Ключ",
    "Резолюция",
    "Создано",
    "Дата завершения",
    "Теги",
    "Original Story Points",
}

REQUIRED_FLOW_COLUMNS = {
    "Задача",
    "Lead Time",
}

PRIORITY_MAP = {
    "low": "Низкий",
    "низкий": "Низкий",
    "minor": "Низкий",
    "medium": "Средний",
    "средний": "Средний",
    "normal": "Средний",
    "high": "Высокий",
    "высокий": "Высокий",
    "critical": "Критический",
    "blocker": "Критический",
    "критический": "Критический",
}

TYPE_MAP = {
    "задача": "Задача",
    "task": "Задача",
    "ошибка": "Баг",
    "bug": "Баг",
    "technical task": "Техническая",
    "tech": "Техническая",
    "story": "Задача",
}


def _check_columns(df: pd.DataFrame, required: set[str], source: str) -> None:
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"В файле {source} отсутствуют обязательные колонки: {missing}")


def _normalize_story_points(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str).str.replace(",", ".", regex=False),
        errors="coerce",
    ).fillna(0)


def build_dataset(
    tasks_path: Path = RAW_TASKS,
    flow_path: Path = RAW_FLOW,
    out_file: Path = OUT_FILE,
) -> pd.DataFrame:
    tasks = pd.read_excel(tasks_path)
    flow = pd.read_csv(flow_path)

    _check_columns(tasks, REQUIRED_TASK_COLUMNS, str(tasks_path))
    _check_columns(flow, REQUIRED_FLOW_COLUMNS, str(flow_path))

    tasks = tasks[
        tasks["Резолюция"].astype(str).str.strip().str.lower() == "решен"
    ].copy()

    tasks["Создано"] = pd.to_datetime(tasks["Создано"], errors="coerce")
    tasks["Дата завершения"] = pd.to_datetime(tasks["Дата завершения"], errors="coerce")
    flow["Lead Time"] = pd.to_numeric(flow["Lead Time"], errors="coerce")

    df = tasks.merge(flow, left_on="Ключ", right_on="Задача", how="inner")
    df = df.dropna(subset=["Создано", "Lead Time"])
    df = df[df["Lead Time"] > 0].copy()

    df["target_hours"] = df["Lead Time"] * 24
    df["story_points"] = _normalize_story_points(df["Original Story Points"])

    df["priority"] = (
        df["Приоритет"]
        .astype(str)
        .str.strip()
        .str.lower()
        .map(PRIORITY_MAP)
        .fillna("Средний")
    )

    df["type"] = (
        df["Тип"]
        .astype(str)
        .str.strip()
        .str.lower()
        .map(TYPE_MAP)
        .fillna(df["Тип"].astype(str).str.strip())
    )

    df["team"] = df["Теги"].apply(extract_team)
    df["created_dow"] = df["Создано"].dt.weekday
    df["created_month"] = df["Создано"].dt.month

    final = df[
        [
            "story_points",
            "priority",
            "type",
            "team",
            "created_dow",
            "created_month",
            "target_hours",
        ]
    ].reset_index(drop=True)

    out_file.parent.mkdir(parents=True, exist_ok=True)
    final.to_csv(out_file, index=False)

    return final


def main() -> None:
    dataset = build_dataset()
    print(f"Saved: {OUT_FILE}")
    print(f"Rows: {len(dataset)}")
    print(dataset["team"].value_counts().to_string())


if __name__ == "__main__":
    main()
