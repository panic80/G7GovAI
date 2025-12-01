import { useState, useCallback, useRef, useEffect } from 'react';
import { CONFIG } from '../../../config';
import type { SampleDataProgressState, SampleDataFile, IngestionLog } from '../types';
import { SAMPLE_FILE_TITLES } from '../types';

interface UseSampleDataOptions {
  onComplete?: () => void;
}

export function useSampleData(options: UseSampleDataOptions = {}) {
  const { onComplete } = options;

  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState<SampleDataProgressState | null>(null);
  const [files, setFiles] = useState<SampleDataFile[]>([]);
  const listRef = useRef<HTMLDivElement>(null);

  // Auto-scroll file list to bottom
  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [files, progress]);

  const loadSampleData = useCallback(async (
    confirmMessage: string,
    addLog: (msg: string, type: IngestionLog['type']) => void
  ) => {
    if (loading) return;

    const confirmed = window.confirm(confirmMessage);
    if (!confirmed) return;

    setLoading(true);
    setProgress({ message: 'Starting...', progress: 0 });
    setFiles([]);
    addLog('Starting sample data ingestion...', 'info');

    let currentFileIndex = -1;
    const seenFiles = new Set<string>();

    try {
      const response = await fetch(`${CONFIG.RAG.BASE_URL}/knowledge-base/ingest-sample-data`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error(`HTTP error: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) throw new Error('No response body');

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n').filter(Boolean);

        for (const line of lines) {
          try {
            const data = JSON.parse(line);
            const progressValue = data.overall_progress || data.progress || 0;
            const message = data.message || data.current_file || '';

            setProgress({
              message,
              progress: progressValue,
              currentFile: data.current_file,
              fileIndex: data.file_index,
              totalFiles: data.total_files,
              phase: data.phase,
              model: data.model,
            });

            // Track file list and statuses
            if (data.current_file && !seenFiles.has(data.current_file)) {
              seenFiles.add(data.current_file);
              setFiles(prev => [...prev, {
                name: data.current_file,
                title: SAMPLE_FILE_TITLES[data.current_file] || data.current_file.replace(/[_-]/g, ' ').replace(/\.\w+$/, ''),
                status: 'processing',
                phase: data.phase,
              }]);
              currentFileIndex = (data.file_index || 1) - 1;
            }

            // Update current file status
            if (data.current_file) {
              setFiles(prev => prev.map((f, idx) =>
                f.name === data.current_file
                  ? { ...f, status: 'processing', phase: data.phase }
                  : idx < currentFileIndex
                    ? { ...f, status: 'complete', phase: 'complete' }
                    : f
              ));
            }

            if (data.phase === 'complete' && !data.current_file) {
              // Final completion - mark all as complete
              setFiles(prev => prev.map(f => ({ ...f, status: 'complete', phase: 'complete' })));
              addLog(`Sample data ingestion complete: ${message}`, 'success');
            } else if (data.phase === 'error') {
              setFiles(prev => prev.map(f =>
                f.name === data.current_file ? { ...f, status: 'error' } : f
              ));
              addLog(`Error: ${message}`, 'error');
            }
          } catch {
            // Skip non-JSON lines
          }
        }
      }

      onComplete?.();
      addLog('Sample data loaded successfully!', 'success');

    } catch (error) {
      console.error('Error loading sample data:', error);
      addLog(`Failed to load sample data: ${error}`, 'error');
    } finally {
      setLoading(false);
      // Keep progress visible for a moment after completion
      setTimeout(() => {
        setProgress(null);
        setFiles([]);
      }, 3000);
    }
  }, [loading, onComplete]);

  return {
    loading,
    progress,
    files,
    listRef,
    loadSampleData,
  };
}
