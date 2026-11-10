"""Voice routes: MiMo ASR transcription and MiMo TTS speech.

Swagger UI renders audio responses as its native player, but it hands the
player the request URL, so a POST response cannot be played (the player would
issue a GET to the POST-only route). The ``GET /api/voice/speech`` variant
therefore carries the synthesis input in the query string; Swagger UI's player
loads that URL and plays the audio. The POST variant stays the canonical
client API, and ``/api/voice/speech/player`` is a standalone local player page.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Query, Response, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from .. import streaming
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
_TTS_FORMATS = ["wav", "mp3", "pcm", "pcm16"]
_TTS_VOICES = [
    "mimo_default",
    "冰糖",
    "茉莉",
    "苏打",
    "白桦",
    "Mia",
    "Chloe",
    "Milo",
    "Dean",
]
_TTS_MODEL_ALIASES = ["default", "voiceclone", "voicedesign"]
GENERIC_UNAVAILABLE = "The model is temporarily unavailable. Please try again."

_TTS_PLAYER_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Verifiable Tutor TTS player</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         max-width: 46rem; margin: 3rem auto; padding: 0 1rem; line-height: 1.5; }
  label { display: block; margin: 1rem 0 .25rem; font-weight: 600; }
  textarea, input, select { width: 100%; padding: .5rem; font: inherit;
                            box-sizing: border-box; }
  textarea { min-height: 7rem; }
  button { margin-top: 1rem; padding: .55rem 1.2rem; font: inherit;
           cursor: pointer; }
  #status { margin-top: 1rem; white-space: pre-wrap; color: #444; }
  #player { display: none; margin-top: 1rem; width: 100%; }
  .hint { color: #666; font-size: .9rem; }
</style>
</head>
<body>
<h1>MiMo TTS player</h1>
<p class="hint">This local page calls <code>POST /api/voice/speech</code> with your
same-origin session cookie and plays the returned audio. Sign in first in
<a href="/docs">/docs</a> (POST /api/auth/login) or the API will answer 401.</p>
<label for="text">Text</label>
<textarea id="text">MPI_Allreduce combines values from all ranks into one result.</textarea>
<label for="voice">Voice (optional)</label>
<input id="voice" placeholder="leave empty for the configured default">
<label for="format">Format</label>
<select id="format">
  <option value="wav" selected>wav</option>
  <option value="mp3">mp3</option>
</select>
<button id="play">Play</button>
<audio id="player" controls></audio>
<div id="status"></div>
<script>
const playButton = document.getElementById("play");
const statusBox = document.getElementById("status");
const player = document.getElementById("player");
playButton.addEventListener("click", async () => {
  const text = document.getElementById("text").value.trim();
  const format = document.getElementById("format").value;
  const voice = document.getElementById("voice").value.trim();
  if (!text) { statusBox.textContent = "Enter some text first."; return; }
  const payload = { text, format };
  if (voice) { payload.voice = voice; }
  statusBox.textContent = "Synthesizing...";
  playButton.disabled = true;
  try {
    const response = await fetch("/api/voice/speech", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const detail = await response.text();
      statusBox.textContent = `HTTP ${response.status}: ${detail}\\n` +
        "If this is a 401, sign in through /docs first.";
      return;
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    player.src = url;
    player.style.display = "block";
    await player.play();
    statusBox.textContent =
      `Received ${blob.size} bytes (${blob.type || "unknown type"}).`;
  } catch (error) {
    statusBox.textContent = `Request failed: ${error}`;
  } finally {
    playButton.disabled = false;
  }
});
</script>
</body>
</html>
"""


class SpeechBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(
        description=(
            "Text to synthesize. "
            "Example: MPI_Allreduce combines values from all ranks."
        )
    )
    voice: str | None = Field(
        default=None,
        description=(
            "Configured TTS voice id; options: mimo_default, 冰糖, 茉莉, 苏打, "
            "白桦, Mia, Chloe, Milo, Dean. Empty uses the configured default."
        ),
    )
    format: str | None = Field(
        default=None,
        description=(
            "Audio format; one of wav, mp3, pcm, or pcm16. Example: wav."
        ),
    )
    model_alias: str = Field(
        default="default",
        description=(
            "TTS model alias; one of default, voiceclone, or voicedesign. "
            "Example: default."
        ),
    )


class SpeechStreamBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(
        description="Text to synthesize. Example: MPI_Allreduce combines values from all ranks."
    )
    voice: str | None = Field(
        default=None,
        description="Configured TTS voice id; empty uses the configured default.",
    )


_STREAM_HEADERS = {"cache-control": "no-cache"}


def _model_failure(exc: Exception) -> HTTPException:
    if isinstance(exc, (CapabilityError, ModelSelectionError)):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, ModelResponseError):
        return HTTPException(status_code=503, detail=exc.user_message)
    if isinstance(exc, ProviderAPIError):
        return HTTPException(status_code=503, detail=GENERIC_UNAVAILABLE)
    return HTTPException(status_code=503, detail=GENERIC_UNAVAILABLE)


def _audio_content() -> dict[str, object]:
    return {
        "audio/wav": {"schema": {"type": "string", "format": "binary"}},
        "audio/mpeg": {"schema": {"type": "string", "format": "binary"}},
        "audio/pcm": {"schema": {"type": "string", "format": "binary"}},
    }


def _synthesize(
    model: object,
    *,
    text: str,
    voice: str | None,
    format: str | None,
    model_alias: str,
) -> Response:
    if not text.strip():
        raise HTTPException(status_code=400, detail="text must not be empty")
    try:
        result = model.speak(
            text,
            voice=voice,
            format=format,
            model_alias=model_alias,
        )
    except (CapabilityError, ModelSelectionError, ModelResponseError, ProviderAPIError) as exc:
        raise _model_failure(exc) from exc
    media_type = _MEDIA_TYPES.get(result.format, "application/octet-stream")
    return Response(content=result.audio, media_type=media_type)


@router.get("/api/voice/speech/player", include_in_schema=False)
def speech_player() -> HTMLResponse:
    """Serve a small local player for auditioning the TTS output."""

    return HTMLResponse(_TTS_PLAYER_HTML)


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


@router.get(
    "/api/voice/speech",
    response_class=Response,
    summary="Synthesize speech and play it in Swagger UI",
    description=(
        "GET variant of the TTS route. Swagger UI's native audio player loads "
        "the request URL, so this variant carries the synthesis input in the "
        "query string and returns the audio bytes; executing it in Swagger UI "
        "plays the result. It triggers one MiMo TTS call per load. Use the POST "
        "variant for clients, longer text, and scripted calls."
    ),
    responses={
        200: {
            "description": "Audio bytes; the media type follows the requested format.",
            "content": _audio_content(),
        },
        400: {"description": "Blank text or unsupported voice or format."},
        401: {"description": "Not signed in."},
        422: {"description": "Missing or invalid query parameter."},
        503: {"description": "Model layer unavailable."},
    },
)
def speech_get(
    user: CurrentUser,
    model: ModelDep,
    text: Annotated[
        str,
        Query(
            min_length=1,
            max_length=2000,
            description=(
                "Text to synthesize. Keep it URL-sized; use the POST variant "
                "for longer text."
            ),
            json_schema_extra={
                "example": "MPI_Allreduce combines values from all ranks."
            },
            openapi_examples={
                "default": {
                    "summary": "Course question text",
                    "value": "MPI_Allreduce combines values from all ranks.",
                }
            },
        ),
    ],
    voice: Annotated[
        str | None,
        Query(
            description="Configured TTS voice id; empty uses the default.",
            json_schema_extra={"example": "Mia", "enum": _TTS_VOICES},
            openapi_examples={
                "default": {"summary": "A configured voice", "value": "Mia"}
            },
        ),
    ] = None,
    format: Annotated[
        str | None,
        Query(
            description="wav, mp3, pcm, or pcm16; empty uses the default.",
            json_schema_extra={"example": "wav", "enum": _TTS_FORMATS},
            openapi_examples={
                "default": {"summary": "WAV audio", "value": "wav"}
            },
        ),
    ] = None,
    model_alias: Annotated[
        str,
        Query(
            description="TTS model alias: default, voiceclone, or voicedesign.",
            json_schema_extra={
                "example": "default",
                "enum": _TTS_MODEL_ALIASES,
            },
            openapi_examples={
                "default": {"summary": "The default TTS model", "value": "default"}
            },
        ),
    ] = "default",
):
    """Synthesize speech from query parameters so the player can load it."""

    return _synthesize(
        model,
        text=text,
        voice=voice,
        format=format,
        model_alias=model_alias,
    )


@router.post(
    "/api/voice/speech",
    response_class=Response,
    summary="Synthesize speech with MiMo TTS",
    description=(
        "Synthesize speech and return the audio bytes. The response media "
        "type follows the requested format (wav, mp3, or pcm). For an audio "
        "player in Swagger UI use the GET variant on the same path; the POST "
        "variant is the canonical client API."
    ),
    responses={
        200: {
            "description": "Audio bytes; the media type follows the requested format.",
            "content": _audio_content(),
        },
        400: {"description": "Blank text or unsupported voice or format."},
        401: {"description": "Not signed in."},
        503: {"description": "Model layer unavailable."},
    },
)
def speech(body: SpeechBody, user: CurrentUser, model: ModelDep):
    """Synthesize one text with MiMo TTS and return the audio bytes."""

    return _synthesize(
        model,
        text=body.text,
        voice=body.voice,
        format=body.format,
        model_alias=body.model_alias,
    )


@router.post(
    "/api/voice/speech/stream",
    summary="Stream synthesized speech as PCM16 frames",
    description=(
        "Synthesize speech and stream base64 PCM16 audio frames as server-sent "
        "events. Each frame carries an audio field, and the stream ends with "
        "the [DONE] marker. The model alias and audio format are fixed here."
    ),
    responses={
        200: {
            "description": "SSE frames with base64 PCM16 audio, ending with [DONE].",
            "content": {"text/event-stream": {"schema": {"type": "string"}}},
        },
        400: {"description": "Blank text."},
        401: {"description": "Not signed in."},
        422: {"description": "Missing or invalid request field."},
        503: {"description": "Model layer unavailable."},
    },
)
def speech_stream(body: SpeechStreamBody, user: CurrentUser, model: ModelDep):
    """Stream one Answer as PCM16 audio frames."""

    if not body.text.strip():
        raise HTTPException(status_code=400, detail="text must not be empty")

    frames = model.speak_stream(body.text, voice=body.voice)
    try:
        first = next(frames, None)
    except (
        CapabilityError,
        ModelSelectionError,
        ModelResponseError,
        ProviderAPIError,
    ) as exc:
        raise _model_failure(exc) from exc

    def body_stream():
        if first is not None:
            yield streaming.sse({"audio": first})
        try:
            for frame in frames:
                yield streaming.sse({"audio": frame})
        except (
            CapabilityError,
            ModelSelectionError,
            ModelResponseError,
            ProviderAPIError,
        ) as exc:
            failure = _model_failure(exc)
            yield streaming.sse(streaming.error(str(failure.detail)))
        yield streaming.DONE_FRAME

    return StreamingResponse(
        body_stream(),
        media_type=streaming.STREAM_MEDIA_TYPE,
        headers=_STREAM_HEADERS,
    )
