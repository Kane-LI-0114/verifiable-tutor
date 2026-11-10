import { ApiError, NETWORK_ERROR_STATUS } from "./client";
import { detailFromPayload, isAbortError } from "./http";

/**
 * Flatten an answer's Markdown into words a voice model can read aloud.
 * Structure and delimiters go away, readable words stay, and nothing is
 * truncated because the backend owns the text length policy.
 */
function toSpeechText(markdown: string): string {
  return markdown
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => !/^(?:```|~~~)/.test(line))
    .map((line) =>
      line.replace(/^(?:#{1,6}\s+|>\s?|[-*+]\s+|\d+\.\s+)/, ""),
    )
    .map((line) =>
      line
        .replace(/!\[([^\]]*)\]\([^)]*\)/g, "$1")
        .replace(/\[([^\]]*)\]\([^)]*\)/g, "$1"),
    )
    .map((line) => line.replace(/\*\*|__|`|\$/g, ""))
    .map((line) =>
      line.replace(/\\/g, "").replace(/[{}]/g, "").replace(/[\^_]/g, " "),
    )
    .map((line) => line.replace(/\s+/g, " ").trim())
    .filter((line) => line.length > 0)
    .join("\n");
}

/** Synthesize one answer as audio bytes from the local TTS endpoint. */
export async function synthesizeSpeech(
  text: string,
  signal?: AbortSignal,
): Promise<Blob> {
  let response: Response;
  try {
    response = await fetch("/api/voice/speech", {
      method: "POST",
      credentials: "same-origin",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ text: toSpeechText(text) }),
      signal,
    });
  } catch (error) {
    if (isAbortError(error)) {
      throw error;
    }
    throw new ApiError(NETWORK_ERROR_STATUS, "network error");
  }
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
