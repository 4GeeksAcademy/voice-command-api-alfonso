from fastapi import APIRouter

from src.app.schemas.voice import InstructionPayload, InstructionRequest
from src.app.services.instructions import route_instruction

router = APIRouter(tags=["instruction"])


@router.post("/instruction", response_model=InstructionPayload)
async def instruction_endpoint(
    payload: InstructionRequest,
) -> InstructionPayload:
    return await route_instruction(payload.transcription)
