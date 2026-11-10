/** Raw PCM16 is 24 kHz, mono, and 16-bit little endian (MiMo TTS). */
export const PCM_SAMPLE_RATE = 24000;

export interface PcmPlayer {
  resume(): Promise<void>;
  enqueue(samples: Int16Array): void;
  stop(): void;
}

/** Queue raw PCM16 chunks onto one Web Audio timeline without gaps. */
export function createPcmPlayer(onFinished?: () => void): PcmPlayer {
  const context = new AudioContext();
  const sources: AudioBufferSourceNode[] = [];
  let nextStartTime = context.currentTime;
  let pending = 0;
  let stopped = false;

  function finish() {
    if (stopped || pending > 0) {
      return;
    }
    stopped = true;
    void context.close();
    onFinished?.();
  }

  return {
    resume() {
      return context.resume();
    },
    enqueue(samples) {
      if (stopped || samples.length === 0) {
        return;
      }
      const buffer = context.createBuffer(1, samples.length, PCM_SAMPLE_RATE);
      const channel = new Float32Array(samples.length);
      for (let index = 0; index < samples.length; index += 1) {
        channel[index] = samples[index] / 32768;
      }
      buffer.copyToChannel(channel, 0);
      const source = context.createBufferSource();
      source.buffer = buffer;
      source.connect(context.destination);
      const startAt = Math.max(context.currentTime, nextStartTime);
      source.start(startAt);
      nextStartTime = startAt + buffer.duration;
      sources.push(source);
      pending += 1;
      source.onended = () => {
        pending -= 1;
        if (pending === 0) {
          finish();
        }
      };
    },
    stop() {
      if (stopped) {
        return;
      }
      stopped = true;
      for (const source of sources) {
        try {
          source.stop();
        } catch {
          // A source that already ended cannot be stopped twice.
        }
      }
      void context.close();
    },
  };
}
