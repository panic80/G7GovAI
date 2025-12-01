/**
 * Shared utilities for streaming stores
 *
 * Consolidates common patterns across govLensStore, lexGraphStore,
 * foresightStore, and accessBridgeStore.
 */

import type { StoreApi } from 'zustand';

// =============================================================================
// History Limits (normalized across all stores)
// =============================================================================

export const HISTORY_LIMITS = {
  QA_PAIRS: 20,          // GovLens Q&A pairs
  EVALUATIONS: 50,       // LexGraph evaluations
  PLANNING_SESSIONS: 30, // ForesightOps planning sessions
  ACCESS_SESSIONS: 30,   // AccessBridge sessions
  UPLOAD_HISTORY: 100,   // KnowledgeBase upload history
} as const;

// =============================================================================
// Streaming State Interface
// =============================================================================

export interface StreamingState {
  loading: boolean;
  error: string | null;
  abortController: AbortController | null;
}

// =============================================================================
// Cancel Handler Factory
// =============================================================================

/**
 * Creates a cancel handler for aborting streaming requests.
 * Used by all 4 streaming stores.
 */
export function createCancelHandler<T extends StreamingState>(
  get: () => T,
  set: StoreApi<T>['setState']
) {
  return () => {
    const controller = get().abortController;
    if (controller) {
      controller.abort();
      set({ abortController: null, loading: false } as Partial<T>);
    }
  };
}

// =============================================================================
// Streaming Request Setup
// =============================================================================

/**
 * Sets up a new streaming request with abort controller.
 * Returns the new controller.
 */
export function setupStreamingRequest<T extends StreamingState>(
  get: () => T,
  set: StoreApi<T>['setState'],
  additionalResetState?: Partial<T>
): AbortController {
  // Abort any existing request
  get().abortController?.abort();

  const controller = new AbortController();

  set({
    abortController: controller,
    loading: true,
    error: null,
    ...additionalResetState,
  } as Partial<T>);

  return controller;
}

// =============================================================================
// Error Handler
// =============================================================================

/**
 * Standard error handler for streaming requests.
 * Silently ignores abort errors, logs others in dev mode.
 */
export function handleStreamingError(
  err: unknown,
  controller: AbortController,
  onError?: (error: string) => void
): boolean {
  // Check if aborted - return true to indicate early exit
  if (controller.signal.aborted || (err as Error)?.name === 'AbortError') {
    return true;
  }

  // Log in development
  if (import.meta.env.DEV) {
    console.error('Streaming error:', err);
  }

  // Call error callback if provided
  if (onError) {
    onError(String(err));
  }

  return false;
}

// =============================================================================
// Cleanup Handler
// =============================================================================

/**
 * Standard finally block for streaming requests.
 * Only updates loading state if not aborted.
 */
export function cleanupStreamingRequest<T extends StreamingState>(
  controller: AbortController,
  set: StoreApi<T>['setState']
): void {
  if (!controller.signal.aborted) {
    set({ loading: false } as Partial<T>);
  }
}

// =============================================================================
// History Management
// =============================================================================

/**
 * Adds an item to a history array with limit enforcement.
 */
export function addToHistory<T>(
  history: T[],
  newItem: T,
  limit: number
): T[] {
  return [...history, newItem].slice(-limit);
}

/**
 * Creates a timestamped history item with UUID.
 */
export function createHistoryItem<T extends object>(
  data: T
): T & { id: string; timestamp: string } {
  return {
    ...data,
    id: crypto.randomUUID(),
    timestamp: new Date().toISOString(),
  };
}
