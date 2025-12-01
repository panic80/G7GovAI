/**
 * Unified API client for GovAI backend communication.
 *
 * Provides:
 * - Standard HTTP methods (GET, POST, DELETE)
 * - Streaming support for NDJSON responses
 * - Consistent error handling
 * - Request/response type safety
 */

import { CONFIG } from '../config';

// =============================================================================
// Types
// =============================================================================

export interface ApiError extends Error {
  status: number;
  statusText: string;
  detail?: string;
}

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'DELETE';
  body?: unknown;
  headers?: Record<string, string>;
  signal?: AbortSignal;
}

// =============================================================================
// Error Handling
// =============================================================================

/**
 * Create a typed API error from a failed response.
 */
async function createApiError(response: Response): Promise<ApiError> {
  let detail: string | undefined;

  try {
    const data = await response.json();
    detail = data.detail || data.message || JSON.stringify(data);
  } catch {
    detail = response.statusText;
  }

  const error = new Error(`API Error: ${response.status} ${response.statusText}`) as ApiError;
  error.status = response.status;
  error.statusText = response.statusText;
  error.detail = detail;

  return error;
}

// =============================================================================
// Standard API Calls
// =============================================================================

/**
 * Make an API call with automatic JSON handling.
 *
 * @param endpoint - API endpoint path (e.g., '/search')
 * @param options - Request options
 * @returns Parsed JSON response
 * @throws ApiError if the request fails
 *
 * @example
 * const results = await apiCall<SearchResult[]>('/search', {
 *   method: 'POST',
 *   body: { query: 'test' }
 * });
 */
export async function apiCall<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const { method = 'GET', body, headers = {}, signal } = options;

  const response = await fetch(`${CONFIG.RAG.BASE_URL}${endpoint}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
    body: body ? JSON.stringify(body) : undefined,
    signal,
  });

  if (!response.ok) {
    throw await createApiError(response);
  }

  return response.json();
}

/**
 * GET request helper.
 */
export async function apiGet<T>(
  endpoint: string,
  options?: Omit<RequestOptions, 'method' | 'body'>
): Promise<T> {
  return apiCall<T>(endpoint, { ...options, method: 'GET' });
}

/**
 * POST request helper.
 */
export async function apiPost<T>(
  endpoint: string,
  body: unknown,
  options?: Omit<RequestOptions, 'method' | 'body'>
): Promise<T> {
  return apiCall<T>(endpoint, { ...options, method: 'POST', body });
}

/**
 * DELETE request helper.
 */
export async function apiDelete<T>(
  endpoint: string,
  options?: Omit<RequestOptions, 'method'>
): Promise<T> {
  return apiCall<T>(endpoint, { ...options, method: 'DELETE' });
}

// =============================================================================
// Streaming API Calls
// =============================================================================

/**
 * Stream NDJSON (newline-delimited JSON) from an endpoint.
 *
 * This is an async generator that yields parsed JSON objects as they arrive.
 *
 * @param endpoint - API endpoint path
 * @param body - Request body
 * @param signal - Optional abort signal
 * @yields Parsed JSON objects from each line
 * @throws ApiError if the request fails
 *
 * @example
 * for await (const event of streamJsonLines<StreamEvent>('/agents/stream/govlens', { query: 'test' })) {
 *   console.log('Received:', event);
 * }
 */
export async function* streamJsonLines<T>(
  endpoint: string,
  body: unknown,
  signal?: AbortSignal
): AsyncGenerator<T, void, undefined> {
  const response = await fetch(`${CONFIG.RAG.BASE_URL}${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  });

  if (!response.ok) {
    throw await createApiError(response);
  }

  if (!response.body) {
    throw new Error('Response body is null');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        // Process any remaining data in buffer
        if (buffer.trim()) {
          try {
            yield JSON.parse(buffer) as T;
          } catch {
            // Ignore incomplete JSON at end
          }
        }
        break;
      }

      buffer += decoder.decode(value, { stream: true });

      // Process complete lines
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // Keep incomplete line in buffer

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;

        try {
          yield JSON.parse(trimmed) as T;
        } catch (err) {
          console.warn('Failed to parse stream line:', trimmed, err);
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

/**
 * Stream NDJSON with a callback for each event.
 *
 * This is a convenience wrapper around streamJsonLines for callback-style usage.
 *
 * @param endpoint - API endpoint path
 * @param body - Request body
 * @param onEvent - Callback for each parsed event
 * @param signal - Optional abort signal
 * @returns Promise that resolves when streaming is complete
 *
 * @example
 * await streamWithCallback<StreamEvent>(
 *   '/agents/stream/govlens',
 *   { query: 'test' },
 *   (event) => console.log('Event:', event)
 * );
 */
export async function streamWithCallback<T>(
  endpoint: string,
  body: unknown,
  onEvent: (event: T) => void,
  signal?: AbortSignal
): Promise<void> {
  for await (const event of streamJsonLines<T>(endpoint, body, signal)) {
    onEvent(event);
  }
}

// =============================================================================
// File Upload
// =============================================================================

/**
 * Upload a file with streaming progress.
 *
 * @param endpoint - API endpoint path
 * @param file - File to upload
 * @param additionalFields - Additional form fields
 * @param signal - Optional abort signal
 * @returns Async generator yielding progress events
 */
export async function* uploadFileWithProgress<T>(
  endpoint: string,
  file: File,
  additionalFields?: Record<string, string>,
  signal?: AbortSignal
): AsyncGenerator<T, void, undefined> {
  const formData = new FormData();
  formData.append('file', file);

  if (additionalFields) {
    for (const [key, value] of Object.entries(additionalFields)) {
      formData.append(key, value);
    }
  }

  const response = await fetch(`${CONFIG.RAG.BASE_URL}${endpoint}`, {
    method: 'POST',
    body: formData,
    signal,
  });

  if (!response.ok) {
    throw await createApiError(response);
  }

  if (!response.body) {
    throw new Error('Response body is null');
  }

  // Stream the progress events
  yield* streamJsonLinesFromResponse<T>(response);
}

/**
 * Stream NDJSON from an existing response.
 */
async function* streamJsonLinesFromResponse<T>(
  response: Response
): AsyncGenerator<T, void, undefined> {
  if (!response.body) {
    throw new Error('Response body is null');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        if (buffer.trim()) {
          try {
            yield JSON.parse(buffer) as T;
          } catch {
            // Ignore
          }
        }
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;

        try {
          yield JSON.parse(trimmed) as T;
        } catch {
          // Skip invalid lines
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
