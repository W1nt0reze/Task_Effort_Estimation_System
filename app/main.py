from __future__ import annotations

import logging
import threading

from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import ml_service
from app.database import (
    count_tasks_after_id,
    get_last_retrained_through_task_id,
    init_db,
    insert_task,
    max_task_id,
    set_last_retrained_through_task_id,
)
from app.schemas import (
    MetaResponse,
    PredictRequest,
    PredictResponse,
    TaskCreate,
    TaskCreated,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = REPO_ROOT / "static"

_retrain_lock = threading.Lock()


def _auto_retrain_job() -> None:
    with _retrain_lock:
        try:
            ml_service.merge_and_retrain()
            set_last_retrained_through_task_id(max_task_id())
        except Exception:
            logging.exception("Automatic model retrain failed")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Task Effort Estimation System",
    lifespan=lifespan,
)


@app.get("/api/meta", response_model=MetaResponse)
def api_meta():
    try:
        priorities, types, teams = ml_service.load_meta_from_csv()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return MetaResponse(
        priorities=priorities,
        types=types,
        teams=teams,
        auto_retrain_every_n=ml_service.AUTO_RETRAIN_EVERY_N_NEW_TASKS,
    )


@app.post("/api/tasks", response_model=TaskCreated)
def api_create_task(body: TaskCreate, background_tasks: BackgroundTasks):
    team = ml_service.normalize_team(body.team)
    through_before = get_last_retrained_through_task_id()

    task_id = insert_task(
        title=body.title.strip(),
        priority=body.priority.strip(),
        type=body.type.strip(),
        team=team,
        story_points=body.story_points,
        actual_hours=body.actual_hours,
        created_at=datetime.now(),
    )

    pending = count_tasks_after_id(through_before)
    scheduled = pending >= ml_service.AUTO_RETRAIN_EVERY_N_NEW_TASKS

    if scheduled:
        background_tasks.add_task(_auto_retrain_job)

    return TaskCreated(id=task_id, retrain_scheduled=scheduled)


@app.post("/api/predict", response_model=PredictResponse)
def api_predict(body: PredictRequest):
    try:
        estimated = ml_service.predict_hours(
            priority=body.priority.strip(),
            type=body.type.strip(),
            team=body.team.strip(),
            story_points=body.story_points,
            ref=datetime.now(),
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return PredictResponse(estimated_hours=round(estimated, 2))


@app.get("/")
def serve_index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
