import json

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import ValidationError
from starlette.datastructures import UploadFile

from src.app.core.config import get_settings
from src.app.schemas.voice import (
    InstructionRequest,
    TaskCreate,
    TaskReplace,
    TaskUpdate,
    TranscribeFlowResponse,
)
from src.app.services.instructions import route_instruction
from src.app.services.tasks import (
    add_task,
    list_tasks,
    patch_task,
    remove_task,
    replace_task,
)
from src.app.utils.language import normalize_transcription_language

router = APIRouter(tags=["transcribe"])


@router.get("/")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/transcribe", response_model=TranscribeFlowResponse)
async def transcribe_and_run_flow(request: Request) -> TranscribeFlowResponse:
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("application/json"):
        try:
            instruction_request = InstructionRequest.model_validate(await request.json())
        except (json.JSONDecodeError, ValidationError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Provide a non-empty transcription.",
            ) from exc
        transcription = instruction_request.transcription
    elif content_type.startswith("multipart/form-data"):
        form = await request.form()
        audio_file = form.get("file")
        if not isinstance(audio_file, UploadFile):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="An audio file is required in the 'file' field.",
            )
        language = normalize_transcription_language(form.get("language"))
        audio = await audio_file.read()
        if not audio:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded audio file is empty.",
            )
        transcription = await _transcribe_audio(
            audio_file.filename or "audio.webm",
            audio,
            audio_file.content_type or "application/octet-stream",
            language,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Send JSON transcription or multipart audio.",
        )

    instruction = await route_instruction(transcription)
    try:
        result = _execute_instruction(
            instruction.endpoint,
            instruction.method,
            instruction.params,
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The instruction service returned invalid task parameters.",
        ) from exc
    return TranscribeFlowResponse(
        transcription=transcription,
        instruction=instruction,
        result=result,
    )


async def _transcribe_audio(
    filename: str,
    audio: bytes,
    content_type: str,
    language: str | None,
) -> str:
    from groq import AsyncGroq

    settings = get_settings()
    try:
        async with AsyncGroq(
            api_key=settings.groq_api_key,
            timeout=settings.request_timeout_seconds,
        ) as client:
            options = {"language": language} if language else {}
            response = await client.audio.transcriptions.create(
                model=settings.groq_transcription_model,
                file=(filename, audio, content_type),
                **options,
            )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The audio transcription service could not process the file.",
        ) from exc
    transcription = response.text.strip()
    if not transcription:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The audio transcription service returned no text.",
        )
    return transcription


def _execute_instruction(endpoint: str, method: str, params: dict[str, object]) -> object:
    if endpoint == "/tasks":
        if method == "GET":
            return list_tasks()
        if method == "POST":
            return add_task(TaskCreate.model_validate(params))
    elif endpoint.startswith("/tasks/"):
        try:
            task_id = int(endpoint.removeprefix("/tasks/"))
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The instruction service returned an invalid task ID.",
            ) from exc
        if method == "PUT":
            return replace_task(task_id, TaskReplace.model_validate(params))
        if method == "PATCH":
            return patch_task(task_id, TaskUpdate.model_validate(params))
        if method == "DELETE":
            remove_task(task_id)
            return {"message": "Task deleted successfully"}
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="The instruction service returned an unsupported task operation.",
    )
