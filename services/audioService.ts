import { AUDIO_SAMPLE_RATE } from '../constants';

export class AudioStreamPlayer {
  private audioContext: AudioContext | null = null;
  private source: AudioBufferSourceNode | null = null;

  constructor() {
    // Initialize AudioContext lazily on user interaction
  }

  private getContext(): AudioContext {
    if (!this.audioContext) {
      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)({
        sampleRate: AUDIO_SAMPLE_RATE,
      });
    }
    return this.audioContext;
  }

  async play(base64Audio: string) {
    this.stop(); // Stop any current playback
    
    const ctx = this.getContext();
    if (ctx.state === 'suspended') {
      await ctx.resume();
    }

    const audioBuffer = await this.decodeAudioData(base64Audio, ctx);
    
    this.source = ctx.createBufferSource();
    this.source.buffer = audioBuffer;
    this.source.connect(ctx.destination);
    this.source.start(0);
    
    return new Promise<void>((resolve) => {
      if (this.source) {
        this.source.onended = () => {
          this.source = null;
          resolve();
        };
      }
    });
  }

  stop() {
    if (this.source) {
      try {
        this.source.stop();
      } catch (e) {
        // ignore errors if already stopped
      }
      this.source = null;
    }
  }

  private async decodeAudioData(base64: string, ctx: AudioContext): Promise<AudioBuffer> {
    const binaryString = atob(base64);
    const len = binaryString.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }

    // Convert raw PCM to AudioBuffer
    // Gemini sends 16-bit PCM, 24kHz, Mono
    const dataInt16 = new Int16Array(bytes.buffer);
    const float32Data = new Float32Array(dataInt16.length);
    
    for (let i = 0; i < dataInt16.length; i++) {
      float32Data[i] = dataInt16[i] / 32768.0;
    }

    const buffer = ctx.createBuffer(1, float32Data.length, AUDIO_SAMPLE_RATE);
    buffer.copyToChannel(float32Data, 0);
    return buffer;
  }
}

export const audioPlayer = new AudioStreamPlayer();
