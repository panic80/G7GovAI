import { useCallback } from 'react';
import {
  AccessBridgeStepData,
  AccessBridgeResult,
  ExtractedFieldEnhanced,
  InformationGap,
} from '../types';
import { useAccessBridgeStore, initialStepData, AccessBridgeProcessParams } from '../stores/accessBridgeStore';

export type { AccessBridgeProcessParams };

export interface UseAccessBridgeStreamReturn {
  stepData: AccessBridgeStepData;
  traceLog: string[];
  loading: boolean;
  result: AccessBridgeResult | null;
  error: string | null;
  extractedFields: ExtractedFieldEnhanced[];
  gaps: InformationGap[];
  followUpQuestions: string[];
  hasCriticalGaps: boolean;
  process: (params: AccessBridgeProcessParams) => Promise<void>;
  submitFollowUp: (answers: Record<string, string>) => Promise<void>;
  reset: () => void;
}

export const useAccessBridgeStream = (): UseAccessBridgeStreamReturn => {
  // Get state and actions from store
  const {
    stepData,
    traceLog,
    loading,
    result,
    error,
    extractedFields,
    gaps,
    followUpQuestions,
    hasCriticalGaps,
    reset,
    performProcess,
    submitFollowUp: storeSubmitFollowUp,
  } = useAccessBridgeStore();

  // No cleanup needed - streaming continues in background via store

  const process = useCallback(
    async (params: AccessBridgeProcessParams) => {
      // Delegate to store action - runs in background independent of component lifecycle
      performProcess(params);
    },
    [performProcess]
  );

  const submitFollowUp = useCallback(
    async (answers: Record<string, string>) => {
      // Delegate to store action
      storeSubmitFollowUp(answers);
    },
    [storeSubmitFollowUp]
  );

  return {
    stepData,
    traceLog,
    loading,
    result,
    error,
    extractedFields,
    gaps,
    followUpQuestions,
    hasCriticalGaps,
    process,
    submitFollowUp,
    reset,
  };
};
