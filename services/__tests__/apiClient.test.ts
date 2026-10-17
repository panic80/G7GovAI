// @vitest-environment node

import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  streamJsonLines,
  streamJsonLinesFromResponse,
  streamWithCallback,
  uploadFileWithProgress,
} from '../apiClient';

const encoder = new TextEncoder();

async function collect<T>(events: AsyncIterable<T>): Promise<T[]> {
  const result: T[] = [];
  for await (const event of events) result.push(event);
  return result;
}

function chunkedResponse(): Response {
  const bytes = encoder.encode(
    '{"text":"안녕하세요"}\r\n \t\r\nmalformed json\r\n{"count":2}\r\n{"done":true}'
  );
  const koreanStart = bytes.findIndex((byte) => byte >= 0xe0);
  const boundaries = [0, 3, koreanStart + 1, koreanStart + 2, bytes.length - 5, bytes.length];
  return new Response(
    new ReadableStream<Uint8Array>({
      start(controller) {
        for (let i = 1; i < boundaries.length; i++) {
          controller.enqueue(bytes.slice(boundaries[i - 1], boundaries[i]));
        }
        controller.close();
      },
    })
  );
}

function unfinishedResponse(cancel = vi.fn()): { response: Response; cancel: typeof cancel } {
  return {
    response: new Response(
      new ReadableStream<Uint8Array>({
        start(controller) {
          controller.enqueue(encoder.encode('{"count":1}\n{"count":2}\n'));
        },
        cancel,
      })
    ),
    cancel,
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('streamJsonLinesFromResponse', () => {
  it('keeps split JSON and UTF-8, skips blank or malformed CRLF lines, and parses the EOF record', async () => {
    const response = chunkedResponse();

    await expect(collect(streamJsonLinesFromResponse(response))).resolves.toEqual([
      { text: '안녕하세요' },
      { count: 2 },
      { done: true },
    ]);
    expect(response.body!.locked).toBe(false);
  });

  it('finishes an empty stream and releases its reader', async () => {
    const response = new Response(
      new ReadableStream<Uint8Array>({
        start(controller) {
          controller.close();
        },
      })
    );

    await expect(collect(streamJsonLinesFromResponse(response))).resolves.toEqual([]);
    expect(response.body!.locked).toBe(false);
  });

  it('rejects a null response body', async () => {
    await expect(collect(streamJsonLinesFromResponse(new Response(null)))).rejects.toThrow(
      'Response body is null'
    );
  });

  it('propagates read failures and releases its reader', async () => {
    const failure = new Error('Connection lost');
    const response = new Response(
      new ReadableStream<Uint8Array>({
        pull(controller) {
          controller.error(failure);
        },
      })
    );

    await expect(collect(streamJsonLinesFromResponse(response))).rejects.toBe(failure);
    expect(response.body!.locked).toBe(false);
  });

  it('cancels unfinished input and releases its reader when the consumer stops early', async () => {
    const { response, cancel } = unfinishedResponse();
    const received = [];

    for await (const event of streamJsonLinesFromResponse(response)) {
      received.push(event);
      break;
    }

    expect(received).toEqual([{ count: 1 }]);
    expect(cancel).toHaveBeenCalledOnce();
    expect(response.body!.locked).toBe(false);
  });

  it('rejects malformed input in strict mode and cancels and releases the reader', async () => {
    const cancel = vi.fn();
    const response = new Response(
      new ReadableStream<Uint8Array>({
        start(controller) {
          controller.enqueue(encoder.encode('malformed json\n{"count":2}\n'));
        },
        cancel,
      })
    );

    await expect(
      collect(streamJsonLinesFromResponse(response, { strict: true }))
    ).rejects.toBeInstanceOf(SyntaxError);
    expect(cancel).toHaveBeenCalledOnce();
    expect(response.body!.locked).toBe(false);
  });
});

describe('streaming requests', () => {
  it('posts JSON with the abort signal and uses the shared streaming behavior', async () => {
    const response = chunkedResponse();
    const fetchMock = vi.fn().mockResolvedValue(response);
    vi.stubGlobal('fetch', fetchMock);
    const signal = new AbortController().signal;

    await expect(collect(streamJsonLines('/events', { query: 'budget' }, signal))).resolves.toEqual([
      { text: '안녕하세요' },
      { count: 2 },
      { done: true },
    ]);
    expect(fetchMock).toHaveBeenCalledWith('/api/events', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: 'budget' }),
      signal,
    });
    expect(response.body!.locked).toBe(false);
  });

  it('posts the file and additional form fields with the abort signal and parses the same events', async () => {
    const response = chunkedResponse();
    const fetchMock = vi.fn().mockResolvedValue(response);
    vi.stubGlobal('fetch', fetchMock);
    const signal = new AbortController().signal;
    const file = new File(['budget notes'], 'notes.txt', { type: 'text/plain' });

    await expect(
      collect(uploadFileWithProgress('/upload', file, { collection: 'finance' }, signal))
    ).resolves.toEqual([{ text: '안녕하세요' }, { count: 2 }, { done: true }]);

    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, request] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/upload');
    expect(request).toEqual({ method: 'POST', body: expect.any(FormData), signal });
    const formData = request.body as FormData;
    expect([...formData.keys()]).toEqual(['file', 'collection']);
    expect(formData.get('collection')).toBe('finance');
    const uploaded = formData.get('file') as File;
    expect(uploaded.name).toBe('notes.txt');
    expect(uploaded.type).toBe('text/plain');
    expect(await uploaded.text()).toBe('budget notes');
    expect(response.body!.locked).toBe(false);
  });

  it.each(['JSON', 'upload'] as const)('preserves the ApiError shape for failed %s requests', async (kind) => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: 'Access denied' }), {
          status: 403,
          statusText: 'Forbidden',
          headers: { 'Content-Type': 'application/json' },
        })
      )
    );
    const events = kind === 'JSON'
      ? streamJsonLines('/events', {})
      : uploadFileWithProgress('/upload', new File(['test'], 'test.txt'));

    await expect(collect(events)).rejects.toMatchObject({
      message: 'API Error: 403 Forbidden',
      status: 403,
      statusText: 'Forbidden',
      detail: 'Access denied',
    });
  });

  it('propagates callback failures while cancelling and releasing the stream, even if cancellation rejects', async () => {
    const cancel = vi.fn().mockRejectedValue(new Error('Cancellation failed'));
    const { response } = unfinishedResponse(cancel);
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response));
    const failure = new Error('Callback failed');
    const onEvent = vi.fn(() => {
      throw failure;
    });

    await expect(streamWithCallback('/events', {}, onEvent)).rejects.toBe(failure);
    expect(onEvent).toHaveBeenCalledExactlyOnceWith({ count: 1 });
    expect(cancel).toHaveBeenCalledOnce();
    expect(response.body!.locked).toBe(false);
  });
});
