/** Synthesize one answer as audio bytes from the local TTS endpoint. */
export async function synthesizeSpeech(text: string): Promise<Blob> {
  const response = await fetch("/api/voice/speech", {
    method: "POST",
    credentials: "same-origin",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ text }),
  });
  return response.blob();
}
