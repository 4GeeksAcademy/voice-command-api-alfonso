from fastapi import APIRouter, status

from src.app.schemas.voice import Task, TaskCreate, TaskReplace, TaskUpdate
from src.app.services.tasks import (
    add_task,
    list_tasks,
    patch_task,
    remove_task,
    replace_task as replace_task_record,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[Task])
def get_tasks() -> list[Task]:
    return list_tasks()


@router.post("", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate) -> Task:
    return add_task(payload)


@router.put("/{task_id}", response_model=Task)
def replace_task(
    task_id: int,
    payload: TaskReplace,
) -> Task:
    return replace_task_record(task_id, payload)


@router.patch("/{task_id}", response_model=Task)
def update_task(
    task_id: int,
    payload: TaskUpdate,
) -> Task:
    return patch_task(task_id, payload)


@router.delete("/{task_id}")
def delete_task(task_id: int) -> dict[str, str]:
    remove_task(task_id)
    return {"message": "Task deleted successfully"}
