import { useState, useCallback } from 'react';
import { generateSpeech } from '../services/geminiService';
import { audioPlayer } from '../services/audioService';
import { Language } from '../types';

interface UseSpeechReturn {
  speaking: boolean;
  loading: boolean;
  speak: (text: string, language?: Language) => Promise<void>;
  stop: () => void;
}

/**
 * Custom hook for text-to-speech functionality.
 * Provides a consistent TTS interface across components.
 *
 * @example
 * const { speaking, loading, speak, stop } = useSpeech();
 *
 * // Speak text
 * await speak("Hello world", "en");
 *
 * // Stop playback
 * stop();
 */
export function useSpeech(): UseSpeechReturn {
  const [speaking, setSpeaking] = useState(false);
  const [loading, setLoading] = useState(false);

  const stop = useCallback(() => {
    audioPlayer.stop();
    setSpeaking(false);
  }, []);

  const speak = useCallback(async (text: string, language: Language = Language.EN) => {
    // If already speaking, stop instead
    if (speaking) {
      stop();
      return;
    }

    if (!text?.trim()) return;

    setLoading(true);
    try {
      const audioData = await generateSpeech(text, language);
      setSpeaking(true);
      await audioPlayer.play(audioData);
      setSpeaking(false);
    } catch (err) {
      console.error('TTS Error:', err);
      setSpeaking(false);
    } finally {
      setLoading(false);
    }
  }, [speaking, stop]);

  return { speaking, loading, speak, stop };
}

export default useSpeech;
