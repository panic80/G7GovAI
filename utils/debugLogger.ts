/**
 * Debug logging utilities - only logs in development mode
 *
 * Usage:
 *   import { debugLog, debugError, debugWarn } from '../utils/debugLogger';
 *   debugLog('[Component] Message', data);
 */

export const debugLog = (...args: unknown[]): void => {
  if (import.meta.env.DEV) {
    console.log(...args);
  }
};

export const debugError = (...args: unknown[]): void => {
  if (import.meta.env.DEV) {
    console.error(...args);
  }
};

export const debugWarn = (...args: unknown[]): void => {
  if (import.meta.env.DEV) {
    console.warn(...args);
  }
};
