import { useState, useCallback, useRef, useEffect } from 'react';
import { sttService, languageToLocale } from '../services/speechToText';
import type { STTStatus, STTResult } from '../types';

interface UseSpeechToTextReturn {
  status: STTStatus;
  interimTranscript: string;
  isAvailable: boolean;
  startListening: (language?: string) => void;
  stopListening: () => void;
  error: string | null;
}

export function useSpeechToText(
  onFinalTranscript: (transcript: string) => void,
): UseSpeechToTextReturn {
  const [status, setStatus] = useState<STTStatus>('idle');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [error, setError] = useState<string | null>(null);
  const isAvailable = sttService.isAvailable();
  const isMountedRef = useRef(true);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      sttService.stop();
    };
  }, []);

  const startListening = useCallback(
    (language = 'en') => {
      if (!isAvailable) {
        setError('Speech recognition is not supported in this browser. Please type your message.');
        return;
      }

      setError(null);
      setInterimTranscript('');

      sttService.configure(
        // onResult
        (result: STTResult) => {
          if (!isMountedRef.current) return;
          if (result.isFinal) {
            setInterimTranscript('');
            setStatus('idle');
            if (result.transcript) {
              onFinalTranscript(result.transcript);
            }
          } else {
            setInterimTranscript(result.transcript);
          }
        },
        // onError
        (errorMsg: string) => {
          if (!isMountedRef.current) return;
          setError(errorMsg);
          setStatus('error');
          setInterimTranscript('');
        },
        // onStatus
        (sttStatus) => {
          if (!isMountedRef.current) return;
          if (sttStatus === 'listening') {
            setStatus('listening');
          } else if (sttStatus === 'stopped') {
            setStatus((prev) => (prev === 'listening' ? 'idle' : prev));
            setInterimTranscript('');
          }
        },
      );

      const locale = languageToLocale[language] ?? 'en-US';
      sttService.start(locale);
    },
    [isAvailable, onFinalTranscript],
  );

  const stopListening = useCallback(() => {
    sttService.stop();
    setStatus('idle');
    setInterimTranscript('');
  }, []);

  return {
    status,
    interimTranscript,
    isAvailable,
    startListening,
    stopListening,
    error,
  };
}
