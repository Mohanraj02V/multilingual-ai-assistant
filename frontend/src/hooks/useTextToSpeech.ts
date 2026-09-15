import { useState, useCallback, useEffect, useRef } from 'react';
import { ttsService } from '../services/textToSpeech';
import type { TTSStatus } from '../types';

interface UseTextToSpeechReturn {
  status: TTSStatus;
  isAvailable: boolean;
  speak: (text: string, language?: string) => void;
  pause: () => void;
  resume: () => void;
  stop: () => void;
}

export function useTextToSpeech(): UseTextToSpeechReturn {
  const [status, setStatus] = useState<TTSStatus>('idle');
  const isAvailable = ttsService.isAvailable();
  const isMountedRef = useRef(true);

  useEffect(() => {
    isMountedRef.current = true;

    // Configure the TTS service with status callback
    ttsService.configure((newStatus) => {
      if (isMountedRef.current) {
        setStatus(newStatus === 'stopped' ? 'idle' : newStatus);
      }
    });

    return () => {
      isMountedRef.current = false;
      ttsService.stop();
    };
  }, []);

  const speak = useCallback((text: string, language = 'en') => {
    if (!isAvailable) {
      setStatus('unavailable');
      return;
    }
    ttsService.speak(text, language);
  }, [isAvailable]);

  const pause = useCallback(() => ttsService.pause(), []);
  const resume = useCallback(() => ttsService.resume(), []);
  const stop = useCallback(() => ttsService.stop(), []);

  return { status, isAvailable, speak, pause, resume, stop };
}
