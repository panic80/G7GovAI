/**
 * Shared status styles for step cards and progress indicators
 *
 * Used by:
 * - StepCard component
 * - AccessBridge wizard
 * - LexGraph steps
 * - ForesightOps steps
 */

import React from 'react';
import { Check, X, Loader2 } from 'lucide-react';
import type { StepStatus } from '../../types';

// =============================================================================
// Status Styles
// =============================================================================

/**
 * Card container styles based on status
 */
export const statusStyles: Record<StepStatus, string> = {
  pending: 'bg-gray-50 border-gray-200 opacity-60',
  in_progress: 'bg-gradient-to-r from-blue-50 to-indigo-50 border-gov-blue shadow-gov',
  completed: 'bg-gradient-to-r from-green-50 to-emerald-50 border-green-500',
  error: 'bg-gradient-to-r from-red-50 to-rose-50 border-red-500',
};

/**
 * Badge/indicator styles based on status
 */
export const badgeStyles: Record<StepStatus, string> = {
  pending: 'bg-gray-300 text-gray-600',
  in_progress: 'bg-gradient-to-br from-gov-blue to-gov-accent text-white animate-pulseRing',
  completed: 'bg-gradient-to-br from-green-500 to-emerald-600 text-white',
  error: 'bg-gradient-to-br from-red-500 to-rose-600 text-white',
};

/**
 * Text styles based on status
 */
export const textStyles: Record<StepStatus, string> = {
  pending: 'text-gray-500',
  in_progress: 'text-gov-blue font-semibold',
  completed: 'text-green-800',
  error: 'text-red-800',
};

/**
 * Icon color classes based on status
 */
export const iconStyles: Record<StepStatus, string> = {
  pending: 'text-gray-400',
  in_progress: 'text-gov-blue animate-pulse',
  completed: 'text-green-600',
  error: 'text-red-600',
};

// =============================================================================
// Status Icon Component
// =============================================================================

interface StatusIconProps {
  status: StepStatus;
  size?: number;
}

/**
 * Renders appropriate icon for a given status
 */
export function StatusIcon({ status, size = 14 }: StatusIconProps): React.ReactElement | null {
  switch (status) {
    case 'in_progress':
      return React.createElement(Loader2, {
        size,
        className: 'animate-spin text-gov-blue',
      });
    case 'completed':
      return React.createElement(Check, {
        size,
        className: 'text-green-600 animate-scaleIn',
      });
    case 'error':
      return React.createElement(X, {
        size,
        className: 'text-red-600',
      });
    default:
      return null;
  }
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Get animation class based on status
 */
export function getAnimationClass(status: StepStatus): string {
  switch (status) {
    case 'in_progress':
      return 'scale-[1.02]';
    case 'completed':
      return 'animate-scaleIn';
    default:
      return '';
  }
}

/**
 * Combines status and animation classes for a card
 */
export function getCardClasses(status: StepStatus): string {
  return `${statusStyles[status]} ${getAnimationClass(status)}`;
}
