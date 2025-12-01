import React, { useState, useRef, useCallback, useEffect } from 'react';
import { Mic, Square, Loader2, Volume2 } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';
import { CONFIG } from '../config';

interface VoiceRecorderProps {
  onTranscript: (text: string) => void;
  disabled?: boolean;
}

export const VoiceRecorder: React.FC<VoiceRecorderProps> = ({ onTranscript, disabled = false }) => {
  const { language, t } = useLanguage();
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationRef = useRef<number | null>(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
        mediaRecorderRef.current.stop();
      }
    };
  }, []);

  // Update audio level visualization
  const updateAudioLevel = useCallback(() => {
    if (!analyserRef.current) return;

    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
    analyserRef.current.getByteFrequencyData(dataArray);

    // Calculate average level
    const average = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
    setAudioLevel(average / 255); // Normalize to 0-1

    if (isRecording) {
      animationRef.current = requestAnimationFrame(updateAudioLevel);
    }
  }, [isRecording]);

  const startRecording = useCallback(async () => {
    setError(null);
    audioChunksRef.current = [];

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // Set up audio analyser for visualization
      const audioContext = new AudioContext();
      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      analyserRef.current = analyser;

      // Create MediaRecorder
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4',
      });

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        // Stop all tracks
        stream.getTracks().forEach((track) => track.stop());

        // Process the recording
        if (audioChunksRef.current.length > 0) {
          await processRecording();
        }
      };

      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start(100); // Collect data every 100ms
      setIsRecording(true);

      // Start audio level visualization
      animationRef.current = requestAnimationFrame(updateAudioLevel);
    } catch (err) {
      if (import.meta.env.DEV) console.error('Microphone access failed:', err);
      setError(language === 'fr' ? 'Impossible d\'accéder au microphone' : 'Unable to access microphone');
    }
  }, [language, updateAudioLevel]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
    setAudioLevel(0);

    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
    }
  }, []);

  const processRecording = async () => {
    setIsProcessing(true);
    setError(null);

    try {
      // Combine chunks into a single blob
      const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });

      // Convert to base64
      const reader = new FileReader();
      const base64Promise = new Promise<string>((resolve, reject) => {
        reader.onloadend = () => {
          const base64 = (reader.result as string).split(',')[1];
          resolve(base64);
        };
        reader.onerror = reject;
      });
      reader.readAsDataURL(audioBlob);
      const audioBase64 = await base64Promise;

      // Send to STT endpoint
      const response = await fetch(`${CONFIG.RAG.BASE_URL}/stt`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          audio_base64: audioBase64,
          audio_format: 'webm',
          language: language,
        }),
      });

      if (!response.ok) {
        throw new Error(`STT failed: ${response.status}`);
      }

      const data = await response.json();
      if (data.text) {
        onTranscript(data.text);
      }
    } catch {
      setError(language === 'fr' ? 'Échec de la transcription' : 'Transcription failed');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleClick = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  return (
    <div className="flex flex-col items-center gap-2">
      {/* Recording button with audio level indicator */}
      <button
        onClick={handleClick}
        disabled={disabled || isProcessing}
        className={`
          relative w-16 h-16 rounded-full flex items-center justify-center
          transition-all duration-200
          ${isRecording
            ? 'bg-red-500 hover:bg-red-600'
            : 'bg-gov-blue hover:bg-gov-blue/90'}
          ${disabled || isProcessing ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
        `}
        aria-label={isRecording
          ? (language === 'fr' ? 'Arrêter l\'enregistrement' : 'Stop recording')
          : (language === 'fr' ? 'Commencer l\'enregistrement' : 'Start recording')}
      >
        {/* Audio level ring */}
        {isRecording && (
          <div
            className="absolute inset-0 rounded-full border-4 border-red-300 animate-pulse"
            style={{
              transform: `scale(${1 + audioLevel * 0.3})`,
              opacity: 0.5 + audioLevel * 0.5,
            }}
          />
        )}

        {isProcessing ? (
          <Loader2 className="w-8 h-8 text-white animate-spin" />
        ) : isRecording ? (
          <Square className="w-6 h-6 text-white" />
        ) : (
          <Mic className="w-8 h-8 text-white" />
        )}
      </button>

      {/* Status text */}
      <span className="text-sm text-gray-500">
        {isProcessing
          ? (language === 'fr' ? 'Transcription en cours...' : 'Transcribing...')
          : isRecording
          ? (language === 'fr' ? 'Enregistrement... Cliquez pour arrêter' : 'Recording... Click to stop')
          : (language === 'fr' ? 'Cliquez pour enregistrer' : 'Click to record')}
      </span>

      {/* Error message */}
      {error && (
        <span className="text-sm text-red-500">{error}</span>
      )}

      {/* Audio level bars (visual feedback while recording) */}
      {isRecording && (
        <div className="flex items-end gap-1 h-8">
          {[...Array(5)].map((_, i) => (
            <div
              key={i}
              className="w-2 bg-red-400 rounded-t transition-all duration-75"
              style={{
                height: `${Math.max(4, audioLevel * 32 * (1 + Math.sin(Date.now() / 100 + i)))}px`,
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
};
