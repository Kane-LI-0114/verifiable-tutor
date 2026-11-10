import { ApiError } from "./client";
import { detailFromPayload } from "./http";

/** Synthesize one answer as audio bytes from the local TTS endpoint. */
export async function synthesizeSpeech(text: string): Promise<Blob> {
  const response = await fetch("/api/voice/speech", {
    method: "POST",
    credentials: "same-origin",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!response.ok) {
    let detail = response.statusText || `HTTP ${response.status}`;
    try {
      detail = detailFromPayload(await response.json(), detail);
    } catch {
      // A non-JSON error body keeps the status text.
    }
    throw new ApiError(response.status, detail);
  }
  return response.blob();
}
