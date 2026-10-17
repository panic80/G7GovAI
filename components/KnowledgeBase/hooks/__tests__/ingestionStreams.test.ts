import type { ChangeEvent } from 'react';
import { act, cleanup, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useKnowledgeBaseStore } from '../../../../stores/knowledgeBaseStore';
import { useConnectors } from '../useConnectors';
import { useFileUpload } from '../useFileUpload';
import { useSampleData } from '../useSampleData';

function byteStreamResponse(text: string): Response {
  const bytes = new TextEncoder().encode(text);
  return new Response(new ReadableStream<Uint8Array>({
    start(controller) {
      // Exercise both partial JSON records and multibyte UTF-8 characters.
      for (const byte of bytes) controller.enqueue(Uint8Array.of(byte));
      controller.close();
    },
  }));
}

beforeEach(() => {
  vi.useFakeTimers();
  useKnowledgeBaseStore.setState(useKnowledgeBaseStore.getInitialState(), true);
});

afterEach(() => {
  cleanup();
  vi.clearAllTimers();
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('knowledge base ingestion streams', () => {
  it('keeps split sample records and the final event without a newline', async () => {
    const response = byteStreamResponse([
      JSON.stringify({
        current_file: 'canada_irpr_2024.txt',
        file_index: 1,
        total_files: 1,
        overall_progress: 25,
        message: '분석 중',
        phase: 'analyzing',
        model: 'sample-model',
      }),
      JSON.stringify({ phase: 'complete', overall_progress: 100, message: '완료' }),
    ].join('\n'));
    const fetchMock = vi.fn().mockResolvedValue(response);
    vi.stubGlobal('fetch', fetchMock);
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    const onComplete = vi.fn();
    const addLog = vi.fn();
    const { result } = renderHook(() => useSampleData({ onComplete }));

    await act(async () => {
      await result.current.loadSampleData('Load sample data?', addLog);
    });

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/knowledge-base/ingest-sample-data'),
      { method: 'POST' },
    );
    expect(result.current.loading).toBe(false);
    expect(result.current.progress).toMatchObject({ progress: 100, message: '완료' });
    expect(result.current.files).toEqual([{
      name: 'canada_irpr_2024.txt',
      title: 'Canada Immigration & Refugee Protection Regulations',
      status: 'complete',
      phase: 'complete',
    }]);
    expect(addLog).toHaveBeenCalledWith('Sample data ingestion complete: 완료', 'success');
    expect(onComplete).toHaveBeenCalledTimes(1);
    expect(response.body?.locked).toBe(false);

    act(() => vi.advanceTimersByTime(2999));
    expect(result.current.progress).not.toBeNull();
    act(() => vi.advanceTimersByTime(1));
    expect(result.current.progress).toBeNull();
    expect(result.current.files).toEqual([]);
  });

  it('records a backend file-upload error instead of treating it as malformed JSON', async () => {
    const response = byteStreamResponse(JSON.stringify({
      status: 'error',
      message: 'Embedding service unavailable',
    }));
    const fetchMock = vi.fn().mockResolvedValue(response);
    vi.stubGlobal('fetch', fetchMock);
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    vi.spyOn(console, 'error').mockImplementation(() => {});
    const { result } = renderHook(() => useFileUpload());
    const file = new File(['test document'], 'document.txt', { type: 'text/plain' });

    await act(async () => {
      result.current.handleFileSelect({
        target: { files: [file], value: 'document.txt' },
      } as unknown as ChangeEvent<HTMLInputElement>);
    });

    expect(result.current.completedHistory).toEqual([expect.objectContaining({
      fileName: 'document.txt',
      status: 'error',
      details: 'Embedding service unavailable',
    })]);
    expect(result.current.logs).toContainEqual(expect.objectContaining({
      message: 'Failed to process document.txt: Embedding service unavailable',
      type: 'error',
    }));
    expect(warn).not.toHaveBeenCalled();
    expect(response.body?.locked).toBe(false);
    const [, request] = fetchMock.mock.calls[0];
    expect(request.method).toBe('POST');
    expect(request.body.get('source_type')).toBe('file');
    expect(request.body.get('file').name).toBe('document.txt');
  });

  it('retains the connector completion delay for a final event without a newline', async () => {
    const response = byteStreamResponse(JSON.stringify({
      status: 'complete', progress: 100, message: 'Imported dataset',
    }));
    const fetchMock = vi.fn().mockResolvedValue(response);
    vi.stubGlobal('fetch', fetchMock);
    const onImportComplete = vi.fn();
    const { result } = renderHook(() => useConnectors({ onImportComplete }));

    await act(async () => {
      await result.current.handleImportDataset('canada', 'immigration');
    });

    expect(result.current.importProgress).toEqual({
      phase: 'complete', progress: 100, message: 'Imported dataset',
    });
    act(() => vi.advanceTimersByTime(1999));
    expect(onImportComplete).not.toHaveBeenCalled();
    act(() => vi.advanceTimersByTime(1));
    expect(onImportComplete).toHaveBeenCalledTimes(1);
    expect(result.current.importProgress).toBeNull();
    const [, request] = fetchMock.mock.calls[0];
    expect(request.method).toBe('POST');
    expect(request.body.get('source_type')).toBe('connector');
    expect(request.body.get('connector_id')).toBe('canada');
    expect(request.body.get('dataset_id')).toBe('immigration');
  });

  it('keeps malformed file-upload records fatal to the upload', async () => {
    const response = byteStreamResponse('{invalid json}\n');
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response));
    vi.spyOn(console, 'error').mockImplementation(() => {});
    const { result } = renderHook(() => useFileUpload());

    await act(async () => {
      result.current.handleFileSelect({
        target: { files: [new File(['content'], 'malformed.txt')], value: 'malformed.txt' },
      } as unknown as ChangeEvent<HTMLInputElement>);
    });

    expect(result.current.completedHistory).toEqual([expect.objectContaining({
      fileName: 'malformed.txt',
      status: 'error',
      details: expect.any(String),
    })]);
    expect(response.body?.locked).toBe(false);
  });
});
