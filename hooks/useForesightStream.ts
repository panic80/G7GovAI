import { useCallback } from 'react';
import { useForesightStore, initialStepData, ForesightStepData, ForesightResult, ForesightOptimizeParams } from '../stores/foresightStore';

export type { ForesightOptimizeParams };

export interface UseForesightStreamReturn {
  stepData: ForesightStepData;
  traceLog: string[];
  loading: boolean;
  result: ForesightResult | null;
  error: string | null;
  optimize: (params: ForesightOptimizeParams) => Promise<void>;
  reset: () => void;
}

export const useForesightStream = (): UseForesightStreamReturn => {
  // Get state and actions from store
  const {
    agentStepData: stepData,
    agentTraceLog: traceLog,
    agentLoading: loading,
    agentResult: result,
    agentError: error,
    resetAgent,
    performOptimize,
  } = useForesightStore();

  // No cleanup needed - streaming continues in background via store

  const optimize = useCallback(
    async (params: ForesightOptimizeParams) => {
      // Delegate to store action - runs in background independent of component lifecycle
      performOptimize(params);
    },
    [performOptimize]
  );

  const reset = useCallback(() => {
    resetAgent();
  }, [resetAgent]);

  return { stepData, traceLog, loading, result, error, optimize, reset };
};
