import * as React from 'react';
import { ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw, Home, Bug } from 'lucide-react';

interface ErrorBoundaryProps {
  children: ReactNode;
  /** Optional fallback component to render on error */
  fallback?: ReactNode;
  /** Optional callback when error occurs */
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  /** Whether to show the reset button */
  showReset?: boolean;
  /** Whether to show technical details in development */
  showDetails?: boolean;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  showStack: boolean;
}

/**
 * React Error Boundary component for catching and handling runtime errors.
 *
 * Wraps child components and displays a fallback UI when an error occurs,
 * preventing the entire application from crashing.
 *
 * @example
 * <ErrorBoundary onError={(error) => logError(error)}>
 *   <MyComponent />
 * </ErrorBoundary>
 *
 * @example
 * // With custom fallback
 * <ErrorBoundary fallback={<CustomErrorPage />}>
 *   <MyComponent />
 * </ErrorBoundary>
 */
export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  static defaultProps = {
    showReset: true,
    showDetails: process.env.NODE_ENV === 'development',
  };

  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      showStack: false,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    this.setState({ errorInfo });
    this.props.onError?.(error, errorInfo);

    // Log to console in development
    if (process.env.NODE_ENV === 'development') {
      console.error('ErrorBoundary caught an error:', error, errorInfo);
    }
  }

  handleReset = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      showStack: false,
    });
  };

  handleGoHome = (): void => {
    window.location.href = '/';
  };

  toggleStack = (): void => {
    this.setState((prev) => ({ showStack: !prev.showStack }));
  };

  render(): ReactNode {
    const { hasError, error, errorInfo, showStack } = this.state;
    const { children, fallback, showReset, showDetails } = this.props;

    if (hasError) {
      // Custom fallback if provided
      if (fallback) {
        return fallback;
      }

      // Default error UI
      return (
        <div className="min-h-[400px] flex items-center justify-center p-8">
          <div className="max-w-lg w-full bg-white rounded-xl shadow-lg border border-red-100 overflow-hidden">
            {/* Header */}
            <div className="bg-red-50 px-6 py-4 border-b border-red-100">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-red-100 rounded-full">
                  <AlertTriangle className="w-6 h-6 text-red-600" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-red-900">
                    Something went wrong
                  </h2>
                  <p className="text-sm text-red-600">
                    An unexpected error occurred
                  </p>
                </div>
              </div>
            </div>

            {/* Content */}
            <div className="p-6 space-y-4">
              {/* Error message */}
              <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                <p className="text-sm font-mono text-gray-700">
                  {error?.message || 'Unknown error'}
                </p>
              </div>

              {/* Technical details (dev only) */}
              {showDetails && errorInfo && (
                <div>
                  <button
                    onClick={this.toggleStack}
                    className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 transition"
                  >
                    <Bug className="w-4 h-4" />
                    {showStack ? 'Hide' : 'Show'} technical details
                  </button>

                  {showStack && (
                    <pre className="mt-2 p-4 bg-gray-900 text-gray-100 rounded-lg text-xs overflow-x-auto max-h-48 overflow-y-auto">
                      {error?.stack}
                      {'\n\nComponent Stack:\n'}
                      {errorInfo.componentStack}
                    </pre>
                  )}
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-3 pt-2">
                {showReset && (
                  <button
                    onClick={this.handleReset}
                    className="flex items-center gap-2 px-4 py-2 bg-gov-blue text-white rounded-lg hover:bg-blue-800 transition text-sm font-medium"
                  >
                    <RefreshCw className="w-4 h-4" />
                    Try Again
                  </button>
                )}
                <button
                  onClick={this.handleGoHome}
                  className="flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition text-sm font-medium"
                >
                  <Home className="w-4 h-4" />
                  Go Home
                </button>
              </div>
            </div>

            {/* Footer */}
            <div className="px-6 py-3 bg-gray-50 border-t border-gray-100">
              <p className="text-xs text-gray-500">
                If this problem persists, please contact support.
              </p>
            </div>
          </div>
        </div>
      );
    }

    return children;
  }
}

/**
 * Functional wrapper hook for using ErrorBoundary with function components.
 * Not a true hook since ErrorBoundary must be a class component.
 */
export const withErrorBoundary = <P extends object>(
  WrappedComponent: React.ComponentType<P>,
  errorBoundaryProps?: Omit<ErrorBoundaryProps, 'children'>
) => {
  const WithErrorBoundary = (props: P) => (
    <ErrorBoundary {...errorBoundaryProps}>
      <WrappedComponent {...props} />
    </ErrorBoundary>
  );

  WithErrorBoundary.displayName = `withErrorBoundary(${WrappedComponent.displayName || WrappedComponent.name || 'Component'})`;

  return WithErrorBoundary;
};

export default ErrorBoundary;
