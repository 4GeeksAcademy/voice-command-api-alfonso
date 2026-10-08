from typing import TypedDict

from fastapi import HTTPException, status

from src.app.schemas.voice import Task, TaskCreate, TaskReplace, TaskUpdate


class TaskRecord(TypedDict):
    id: int
    title: str
    done: bool


tasks: list[TaskRecord] = []
_next_task_id = 1


def list_tasks() -> list[Task]:
    return [Task.model_validate(task) for task in tasks]


def add_task(payload: TaskCreate) -> Task:
    global _next_task_id
    task: TaskRecord = {
        "id": _next_task_id,
        "title": payload.title,
        "done": payload.done,
    }
    _next_task_id += 1
    tasks.append(task)
    return Task.model_validate(task)


def replace_task(task_id: int, payload: TaskReplace) -> Task:
    task = _find_task(task_id)
    task["title"] = payload.title
    task["done"] = payload.done
    return Task.model_validate(task)


def patch_task(task_id: int, payload: TaskUpdate) -> Task:
    if not payload.model_fields_set or not any(
        value is not None for value in payload.model_dump().values()
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one non-null task field must be provided.",
        )

    task = _find_task(task_id)
    if payload.title is not None:
        task["title"] = payload.title
    if payload.done is not None:
        task["done"] = payload.done
    return Task.model_validate(task)


def remove_task(task_id: int) -> None:
    task = _find_task(task_id)
    tasks.remove(task)


def _find_task(task_id: int) -> TaskRecord:
    for task in tasks:
        if task["id"] == task_id:
            return task
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Task {task_id} not found.",
    )