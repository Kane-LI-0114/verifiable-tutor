"""Voice routes: MiMo ASR transcription and MiMo TTS speech."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile
from pydantic import BaseModel, ConfigDict

from ..deps import CurrentUser, ModelDep
from ..schemas import TranscriptionResponse
from ...llm.adapter import (
    CapabilityError,
    ModelResponseError,
    ModelSelectionError,
    ProviderAPIError,
)

router = APIRouter(tags=["voice"])

_ALLOWED_AUDIO_TYPES = {"audio/wav", "audio/mpeg", "audio/mp3"}
_MAX_UPLOAD_BYTES = 7_000_000
_MEDIA_TYPES = {
    "wav": "audio/wav",
    "mp3": "audio/mpeg",
    "pcm": "audio/pcm",
    "pcm16": "audio/pcm",
}
GENERIC_UNAVAILABLE = "The model is temporarily unavailable. Please try again."


class SpeechBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    voice: str | None = None
    format: str | None = None
    model_alias: str = "default"


def _model_failure(exc: Exception) -> HTTPException:
    if isinstance(exc, (CapabilityError, ModelSelectionError)):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, ModelResponseError):
        return HTTPException(status_code=503, detail=exc.user_message)
    if isinstance(exc, ProviderAPIError):
        return HTTPException(status_code=503, detail=GENERIC_UNAVAILABLE)
    return HTTPException(status_code=503, detail=GENERIC_UNAVAILABLE)


@router.post(
    "/api/voice/transcriptions",
    response_model=TranscriptionResponse,
    summary="Transcribe an audio file with MiMo ASR",
    responses={
        400: {"description": "Empty or unreadable audio."},
        401: {"description": "Not signed in."},
        413: {"description": "Audio file is too large."},
        415: {"description": "Unsupported audio type."},
        503: {"description": "Model layer unavailable."},
    },
)
def transcribe(
    user: CurrentUser,
    model: ModelDep,
    audio: Annotated[UploadFile, File()],
    language: Annotated[str, Form()] = "auto",
):
    """Transcribe one uploaded audio file with MiMo ASR."""

    data = audio.file.read()
    mime = (audio.content_type or "").split(";")[0].strip().lower()
    if mime not in _ALLOWED_AUDIO_TYPES:
        raise HTTPException(
            status_code=415,
            detail="unsupported audio type; MiMo ASR accepts audio/wav or audio/mpeg",
        )
    if len(data) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="audio file is too large")
    if not data:
        raise HTTPException(status_code=400, detail="audio file is empty")
    try:
        result = model.transcribe(data, mime=mime, language=language)
    except (CapabilityError, ModelSelectionError, ModelResponseError, ProviderAPIError) as exc:
        raise _model_failure(exc) from exc
    return {
        "text": result.text,
        "language": result.language,
        "seconds": result.seconds,
        "model": result.model,
    }


@router.post(
    "/api/voice/speech",
    summary="Synthesize speech with MiMo TTS",
    responses={
        200: {
            "description": (
                "Audio bytes; the media type follows the requested format."
            ),
            "content": {
                "audio/wav": {"schema": {"type": "string", "format": "binary"}},
                "audio/mpeg": {"schema": {"type": "string", "format": "binary"}},
                "audio/pcm": {"schema": {"type": "string", "format": "binary"}},
            },
        },
        400: {"description": "Blank text or unsupported voice or format."},
        401: {"description": "Not signed in."},
        503: {"description": "Model layer unavailable."},
    },
)
def speech(body: SpeechBody, user: CurrentUser, model: ModelDep):
    """Synthesize one text with MiMo TTS and return the audio bytes."""

    if not body.text.strip():
        raise HTTPException(status_code=400, detail="text must not be empty")
    try:
        result = model.speak(
            body.text,
            voice=body.voice,
            format=body.format,
            model_alias=body.model_alias,
        )
    except (CapabilityError, ModelSelectionError, ModelResponseError, ProviderAPIError) as exc:
        raise _model_failure(exc) from exc
    media_type = _MEDIA_TYPES.get(result.format, "application/octet-stream")
    return Response(content=result.audio, media_type=media_type)
