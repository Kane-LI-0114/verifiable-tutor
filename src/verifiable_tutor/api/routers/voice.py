"""Voice routes: MiMo ASR transcription and MiMo TTS speech.

Swagger UI renders JSON and images, not audio responses, so the speech route
documents its binary media types properly (downloadable from Swagger UI) and a
small local player page at ``/api/voice/speech/player`` is served for manual
auditioning with the same-origin session cookie.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import HTMLResponse
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
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "text": "MPI_Allreduce combines values from all ranks.",
                "voice": "Mia",
                "format": "wav",
                "model_alias": "default",
            }
        },
    )

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


@router.post(
    "/api/voice/speech",
    response_class=Response,
    summary="Synthesize speech with MiMo TTS",
    description=(
        "Synthesize speech and return the audio bytes. The response media "
        "type follows the requested format (wav, mp3, or pcm). Swagger UI "
        "cannot play audio responses; open /api/voice/speech/player in a "
        "browser with a signed-in session to audition the output."
    ),
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
