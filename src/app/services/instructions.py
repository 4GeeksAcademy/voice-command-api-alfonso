import re

from fastapi import HTTPException, status
from groq import AsyncGroq
from pydantic import ValidationError

from src.app.core.config import get_settings
from src.app.schemas.voice import InstructionPayload

_SYSTEM_PROMPT = """You route voice commands for a task-list API.
Return only a valid JSON object with exactly these keys: endpoint, method, params.
Never include prose, markdown, or additional keys. Use only these operations:
- List tasks: endpoint "/tasks", method "GET", params {}.
- Create a task: endpoint "/tasks", method "POST", params {"title": string, "done": boolean?}.
- Replace a task: endpoint "/tasks/{id}", method "PUT", params {"title": string, "done": boolean}.
- Update a task: endpoint "/tasks/{id}", method "PATCH", params with only the changed "title" and/or "done".
- Delete a task: endpoint "/tasks/{id}", method "DELETE", params {}.
The id in item endpoints must be the integer task ID mentioned by the user.
Do not invent an ID when the user did not identify a specific existing task.
If the command is not a supported task operation or lacks required information,
return {"endpoint":"/tasks","method":"GET","params":{}}.
"""
_TASK_COLLECTION = "/tasks"
_TASK_ITEM = re.compile(r"^/tasks/([1-9][0-9]*)$")


async def route_instruction(transcription: str) -> InstructionPayload:
    settings = get_settings()
    try:
        async with AsyncGroq(
            api_key=settings.groq_api_key,
            timeout=settings.request_timeout_seconds,
        ) as client:
            response = await client.chat.completions.create(
                model=settings.groq_model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": transcription},
                ],
                response_format={"type": "json_object"},
                temperature=0,
            )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The instruction service could not process the request.",
        ) from exc

    try:
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty completion")
        instruction = InstructionPayload.model_validate_json(content)
    except (IndexError, ValueError, ValidationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The instruction service returned an invalid response.",
        ) from exc

    method = instruction.method.upper()
    item_match = _TASK_ITEM.fullmatch(instruction.endpoint)
    allowed_methods = {"GET", "POST"} if instruction.endpoint == _TASK_COLLECTION else (
        {"PUT", "PATCH", "DELETE"} if item_match else set()
    )
    if method not in allowed_methods:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The instruction service returned an unsupported task route.",
        )
    instruction.method = method
    return instruction