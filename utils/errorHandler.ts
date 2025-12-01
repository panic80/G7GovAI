/**
 * Unified error handling utilities for GovAI frontend.
 *
 * Provides consistent error handling, logging, and user-friendly messages.
 */

import { MAX_RETRY_DELAY_MS, BASE_RETRY_DELAY_MS } from '../constants';

// =============================================================================
// Types
// =============================================================================

export type ErrorSeverity = 'info' | 'warning' | 'error' | 'critical';

export interface ErrorContext {
  /** Module or component where the error occurred */
  module: string;
  /** Action being performed when the error occurred */
  action: string;
  /** Additional metadata for debugging */
  metadata?: Record<string, unknown>;
}

export interface AppError extends Error {
  /** Error severity level */
  severity: ErrorSeverity;
  /** Context where the error occurred */
  context: ErrorContext;
  /** Original error if wrapped */
  cause?: Error;
  /** User-friendly message */
  userMessage: string;
  /** Timestamp when the error occurred */
  timestamp: Date;
}

// =============================================================================
// Error Messages
// =============================================================================

/** User-friendly error messages by category */
const USER_MESSAGES: Record<string, string> = {
  // Network errors
  'network': 'Unable to connect to the server. Please check your connection.',
  'timeout': 'The request took too long. Please try again.',
  'abort': 'The request was cancelled.',

  // API errors
  'api_400': 'Invalid request. Please check your input.',
  'api_401': 'Authentication required. Please log in.',
  'api_403': 'You do not have permission to perform this action.',
  'api_404': 'The requested resource was not found.',
  'api_422': 'Invalid data provided. Please check your input.',
  'api_429': 'Too many requests. Please wait a moment.',
  'api_500': 'A server error occurred. Please try again later.',

  // Generic
  'unknown': 'An unexpected error occurred. Please try again.',
  'parse': 'Unable to process the response.',
};

// =============================================================================
// Error Creation
// =============================================================================

/**
 * Create a standardized AppError from any error.
 *
 * @param error - Original error (can be any type)
 * @param context - Error context information
 * @param severity - Error severity level
 * @returns Standardized AppError
 */
export function createAppError(
  error: unknown,
  context: ErrorContext,
  severity: ErrorSeverity = 'error'
): AppError {
  const cause = error instanceof Error ? error : undefined;
  const message = error instanceof Error ? error.message : String(error);

  const appError = new Error(message) as AppError;
  appError.name = 'AppError';
  appError.severity = severity;
  appError.context = context;
  appError.cause = cause;
  appError.timestamp = new Date();
  appError.userMessage = getUserMessage(error);

  return appError;
}

/**
 * Get a user-friendly message for an error.
 */
function getUserMessage(error: unknown): string {
  if (error instanceof Error) {
    // Check for network errors
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      return USER_MESSAGES['network'];
    }
    if (error.name === 'AbortError') {
      return USER_MESSAGES['abort'];
    }

    // Check for API errors (from apiClient)
    const apiError = error as { status?: number };
    if (typeof apiError.status === 'number') {
      const key = `api_${apiError.status}`;
      return USER_MESSAGES[key] || USER_MESSAGES['unknown'];
    }

    // Check for timeout
    if (error.message.toLowerCase().includes('timeout')) {
      return USER_MESSAGES['timeout'];
    }

    // Check for parse errors
    if (error instanceof SyntaxError) {
      return USER_MESSAGES['parse'];
    }
  }

  return USER_MESSAGES['unknown'];
}

// =============================================================================
// Error Logging
// =============================================================================

/**
 * Log an error with context.
 *
 * In development, logs to console.
 * In production, could be extended to send to monitoring service.
 */
export function logError(
  error: unknown,
  context: ErrorContext,
  severity: ErrorSeverity = 'error'
): void {
  const appError = error instanceof Error && 'severity' in error
    ? error as AppError
    : createAppError(error, context, severity);

  const logData = {
    severity: appError.severity,
    module: appError.context.module,
    action: appError.context.action,
    message: appError.message,
    userMessage: appError.userMessage,
    timestamp: appError.timestamp.toISOString(),
    metadata: appError.context.metadata,
    stack: appError.stack,
  };

  // Log based on severity
  switch (severity) {
    case 'info':
      console.info(`[${context.module}:${context.action}]`, logData);
      break;
    case 'warning':
      console.warn(`[${context.module}:${context.action}]`, logData);
      break;
    case 'critical':
      console.error(`[CRITICAL] [${context.module}:${context.action}]`, logData);
      break;
    default:
      console.error(`[${context.module}:${context.action}]`, logData);
  }

  // TODO: In production, send to monitoring service
  // sendToMonitoring(logData);
}

// =============================================================================
// Error Handling Wrappers
// =============================================================================

/**
 * Wrap an async function with error handling.
 *
 * @param operation - Async function to execute
 * @param context - Error context
 * @param options - Additional options
 * @returns Result of the operation or null on error
 *
 * @example
 * const result = await withErrorHandling(
 *   () => api.search(query),
 *   { module: 'GovLens', action: 'search' },
 *   { onError: (error) => showToast(error.userMessage) }
 * );
 */
export async function withErrorHandling<T>(
  operation: () => Promise<T>,
  context: ErrorContext,
  options?: {
    onError?: (error: AppError) => void;
    rethrow?: boolean;
    severity?: ErrorSeverity;
  }
): Promise<T | null> {
  try {
    return await operation();
  } catch (error) {
    const appError = createAppError(error, context, options?.severity);
    logError(appError, context, options?.severity);

    options?.onError?.(appError);

    if (options?.rethrow) {
      throw appError;
    }

    return null;
  }
}

/**
 * Wrap a sync function with error handling.
 */
export function withErrorHandlingSync<T>(
  operation: () => T,
  context: ErrorContext,
  options?: {
    onError?: (error: AppError) => void;
    rethrow?: boolean;
    severity?: ErrorSeverity;
  }
): T | null {
  try {
    return operation();
  } catch (error) {
    const appError = createAppError(error, context, options?.severity);
    logError(appError, context, options?.severity);

    options?.onError?.(appError);

    if (options?.rethrow) {
      throw appError;
    }

    return null;
  }
}

// =============================================================================
// Error Boundary Helpers
// =============================================================================

/**
 * Check if an error is recoverable.
 *
 * Recoverable errors can be retried or dismissed without crashing the app.
 */
export function isRecoverableError(error: unknown): boolean {
  if (!(error instanceof Error)) return true;

  // API errors are generally recoverable
  const apiError = error as { status?: number };
  if (typeof apiError.status === 'number') {
    // 5xx errors might be temporary
    return apiError.status >= 400;
  }

  // Network errors are recoverable (can retry)
  if (error.name === 'TypeError' || error.name === 'AbortError') {
    return true;
  }

  // Parse errors are recoverable
  if (error instanceof SyntaxError) {
    return true;
  }

  // Default to non-recoverable for unknown errors
  return false;
}

/**
 * Get a retry delay for exponential backoff.
 *
 * @param attempt - Current attempt number (0-indexed)
 * @param baseDelay - Base delay in ms (default 1000)
 * @param maxDelay - Maximum delay in ms (default 30000)
 * @returns Delay in milliseconds with jitter
 */
export function getRetryDelay(
  attempt: number,
  baseDelay: number = BASE_RETRY_DELAY_MS,
  maxDelay: number = MAX_RETRY_DELAY_MS
): number {
  // Exponential backoff: baseDelay * 2^attempt
  const exponentialDelay = baseDelay * Math.pow(2, attempt);

  // Cap at maxDelay
  const cappedDelay = Math.min(exponentialDelay, maxDelay);

  // Add jitter (0-25% random variation)
  const jitter = cappedDelay * 0.25 * Math.random();

  return Math.floor(cappedDelay + jitter);
}
