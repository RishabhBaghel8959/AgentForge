"""Typed contracts shared by the orchestration agents."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class Task(BaseModel):
    id: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=500)
    priority: str = "Medium"
    status: str = "Pending"


class ExecutionPlan(BaseModel):
    document_type: str = Field(min_length=1, max_length=120)
    goal: str = Field(min_length=1, max_length=500)
    assumptions: list[str] = Field(default_factory=list, max_length=10)
    tasks: list[Task] = Field(min_length=1, max_length=8)

    @field_validator("tasks")
    @classmethod
    def unique_task_titles(cls, tasks: list[Task]) -> list[Task]:
        titles = [task.title.casefold() for task in tasks]
        if len(titles) != len(set(titles)):
            raise ValueError("Task titles must be unique.")
        return tasks


class RunStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class WorkflowState(BaseModel):
    run_id: str
    user_id: int
    request: str
    status: RunStatus = RunStatus.RUNNING
    plan: ExecutionPlan | None = None
    draft_sections: dict[str, str] = Field(default_factory=dict)
    reviewed_sections: dict[str, str] = Field(default_factory=dict)
    document_path: str | None = None
    error: str | None = None


class GenerationResult(BaseModel):
    text: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


class RunSnapshot(BaseModel):
    run_id: str
    user_id: int
    request: str
    status: RunStatus
    document_path: str | None = None
    error: str | None = None
    events: list[dict[str, Any]] = Field(default_factory=list)
