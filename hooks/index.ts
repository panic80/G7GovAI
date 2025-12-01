/**
 * GovAI Custom Hooks
 *
 * This module exports all custom React hooks used in the application.
 */

// Generic streaming hook - use this as the base for new streaming implementations
export {
  useStreamingRequest,
  useStepStreamingRequest,
  useStreamingRequestWithResult,
} from './useStreamingRequest';
export type {
  UseStreamingRequestState,
  UseStreamingRequestReturn,
} from './useStreamingRequest';

// Domain-specific streaming hooks
export { useGovLensSearch } from './useGovLensSearch';
export type { SearchFilters, QAPair } from './useGovLensSearch';

export { useAccessBridgeStream } from './useAccessBridgeStream';
export type {
  AccessBridgeProcessParams,
  UseAccessBridgeStreamReturn,
} from './useAccessBridgeStream';

export { useForesightStream } from './useForesightStream';
export type { UseForesightStreamReturn } from './useForesightStream';

export { useLexGraphStream } from './useLexGraphStream';

// Utility hooks
export { useSpeech } from './useSpeech';
export type { default as UseSpeechReturn } from './useSpeech';
