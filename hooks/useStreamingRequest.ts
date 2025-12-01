/**
 * Generic streaming request hook for GovAI.
 *
 * Provides a reusable hook for streaming NDJSON responses with:
 * - Loading state management
 * - Error handling
 * - Request cancellation
 * - Event buffering
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import { streamJsonLines } from '../services/apiClient';

// =============================================================================
// Types
// =============================================================================

export interface UseStreamingRequestState<T> {
  /** Whether a request is currently in progress */
  loading: boolean;
  /** Error message if request failed */
  error: string | null;
  /** All events received so far */
  events: T[];
  /** The most recent event */
  lastEvent: T | null;
}

export interface UseStreamingRequestReturn<TRequest, TEvent> extends UseStreamingRequestState<TEvent> {
  /** Execute a streaming request */
  execute: (endpoint: string, body: TRequest) => Promise<void>;
  /** Cancel the current request */
  abort: () => void;
  /** Reset state to initial values */
  reset: () => void;
  /** Whether a request can be aborted */
  canAbort: boolean;
}

// =============================================================================
// Hook
// =============================================================================

/**
 * Generic hook for streaming NDJSON requests.
 *
 * @param onEvent - Optional callback for each event
 * @param onComplete - Optional callback when streaming completes
 * @param onError - Optional callback when an error occurs
 * @returns Streaming request state and controls
 *
 * @example
 * const { execute, loading, events, error, abort } = useStreamingRequest<
 *   GovLensRequest,
 *   GovLensStreamEvent
 * >({
 *   onEvent: (event) => console.log('Event:', event),
 *   onComplete: () => console.log('Done!'),
 * });
 *
 * // Start streaming
 * await execute('/agents/stream/govlens', { query: 'test' });
 */
export function useStreamingRequest<TRequest, TEvent>(options?: {
  onEvent?: (event: TEvent) => void;
  onComplete?: (events: TEvent[]) => void;
  onError?: (error: Error) => void;
}): UseStreamingRequestReturn<TRequest, TEvent> {
  const { onEvent, onComplete, onError } = options || {};

  // State
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [events, setEvents] = useState<TEvent[]>([]);
  const [lastEvent, setLastEvent] = useState<TEvent | null>(null);

  // Refs
  const abortControllerRef = useRef<AbortController | null>(null);
  const eventsRef = useRef<TEvent[]>([]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  // Reset state
  const reset = useCallback(() => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setLoading(false);
    setError(null);
    setEvents([]);
    setLastEvent(null);
    eventsRef.current = [];
  }, []);

  // Abort current request
  const abort = useCallback(() => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setLoading(false);
  }, []);

  // Execute streaming request
  const execute = useCallback(async (endpoint: string, body: TRequest) => {
    // Cancel any existing request
    abortControllerRef.current?.abort();

    // Create new abort controller
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    // Reset state
    setLoading(true);
    setError(null);
    setEvents([]);
    setLastEvent(null);
    eventsRef.current = [];

    try {
      for await (const event of streamJsonLines<TEvent>(
        endpoint,
        body,
        abortController.signal
      )) {
        // Check if aborted
        if (abortController.signal.aborted) {
          break;
        }

        // Update state
        eventsRef.current = [...eventsRef.current, event];
        setEvents(eventsRef.current);
        setLastEvent(event);

        // Call event callback
        onEvent?.(event);
      }

      // Call complete callback
      if (!abortController.signal.aborted) {
        onComplete?.(eventsRef.current);
      }
    } catch (err) {
      // Ignore abort errors
      if (err instanceof Error && err.name === 'AbortError') {
        return;
      }

      const errorMessage = err instanceof Error ? err.message : 'Stream request failed';
      setError(errorMessage);
      onError?.(err instanceof Error ? err : new Error(errorMessage));
    } finally {
      if (abortControllerRef.current === abortController) {
        setLoading(false);
        abortControllerRef.current = null;
      }
    }
  }, [onEvent, onComplete, onError]);

  return {
    loading,
    error,
    events,
    lastEvent,
    execute,
    abort,
    reset,
    canAbort: loading && abortControllerRef.current !== null,
  };
}

// =============================================================================
// Specialized Hooks
// =============================================================================

/**
 * Hook for streaming with step-based progress tracking.
 *
 * Useful for multi-step agent workflows where you need to track
 * which step is currently active.
 *
 * @param stepField - Field name in events that indicates the step
 * @param options - Standard streaming options
 */
export function useStepStreamingRequest<TRequest, TEvent extends Record<string, unknown>>(
  stepField: keyof TEvent,
  options?: {
    onEvent?: (event: TEvent) => void;
    onComplete?: (events: TEvent[]) => void;
    onError?: (error: Error) => void;
  }
) {
  const [stepData, setStepData] = useState<Record<string, TEvent>>({});
  const [currentStep, setCurrentStep] = useState<string | null>(null);

  const handleEvent = useCallback((event: TEvent) => {
    const step = event[stepField];
    if (typeof step === 'string') {
      setCurrentStep(step);
      setStepData(prev => ({ ...prev, [step]: event }));
    }
    options?.onEvent?.(event);
  }, [stepField, options]);

  const baseHook = useStreamingRequest<TRequest, TEvent>({
    ...options,
    onEvent: handleEvent,
  });

  const reset = useCallback(() => {
    baseHook.reset();
    setStepData({});
    setCurrentStep(null);
  }, [baseHook]);

  return {
    ...baseHook,
    reset,
    stepData,
    currentStep,
  };
}

/**
 * Hook for streaming with automatic JSON parsing of a specific field.
 *
 * Useful when the final event contains a JSON string that needs parsing.
 *
 * @param resultField - Field name containing the JSON string
 * @param options - Standard streaming options
 */
export function useStreamingRequestWithResult<TRequest, TEvent, TResult>(
  resultField: keyof TEvent,
  options?: {
    onEvent?: (event: TEvent) => void;
    onComplete?: (events: TEvent[]) => void;
    onError?: (error: Error) => void;
  }
) {
  const [result, setResult] = useState<TResult | null>(null);

  const handleEvent = useCallback((event: TEvent) => {
    const value = event[resultField];
    if (typeof value === 'string' && value.trim()) {
      try {
        // Try to parse as JSON
        const parsed = JSON.parse(value) as TResult;
        setResult(parsed);
      } catch {
        // Not JSON, might be a string result
        setResult(value as unknown as TResult);
      }
    }
    options?.onEvent?.(event);
  }, [resultField, options]);

  const baseHook = useStreamingRequest<TRequest, TEvent>({
    ...options,
    onEvent: handleEvent,
  });

  const reset = useCallback(() => {
    baseHook.reset();
    setResult(null);
  }, [baseHook]);

  return {
    ...baseHook,
    reset,
    result,
  };
}
