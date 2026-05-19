from __future__ import annotations

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1)
    priority: str = Field(..., min_length=1)
    type: str = Field(..., min_length=1)
    team: str = Field(..., min_length=1)
    story_points: float = Field(0.0, ge=0)
    actual_hours: float = Field(..., gt=0)


class TaskCreated(BaseModel):
    id: int
    retrain_scheduled: bool = False


class PredictRequest(BaseModel):
    priority: str = Field(..., min_length=1)
    type: str = Field(..., min_length=1)
    team: str = Field(..., min_length=1)
    story_points: float = Field(0.0, ge=0)


class PredictResponse(BaseModel):
    estimated_hours: float


class MetaResponse(BaseModel):
    priorities: list[str]
    types: list[str]
    teams: list[str]
    auto_retrain_every_n: int
