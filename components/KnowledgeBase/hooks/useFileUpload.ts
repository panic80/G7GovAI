import React, { useState, useEffect, useCallback } from 'react';
import { CONFIG } from '../../../config';
import { useKnowledgeBaseStore } from '../../../stores/knowledgeBaseStore';
import type { UploadHistoryItem, IngestionLog, UploadStatus, IngestionStep } from '../types';

interface UseFileUploadOptions {
  onComplete?: () => void;
}

export function useFileUpload(options: UseFileUploadOptions = {}) {
  const { onComplete } = options;

  // Get persisted state from store
  const {
    uploadStatus,
    setUploadStatus,
    currentStep,
    setCurrentStep,
    progress,
    setProgress,
    message,
    setMessage,
    showLogs,
    setShowLogs,
    logs,
    setLogs,
    addLog: storeAddLog,
    clearLogs,
    completedHistory,
    addToCompletedHistory,
    stepModels,
    setStepModel,
  } = useKnowledgeBaseStore();

  // File objects cannot be serialized, keep them as local state
  const [queue, setQueue] = useState<File[]>([]);
  const [processingFile, setProcessingFile] = useState<File | null>(null);

  const addLog = useCallback((msg: string, type: IngestionLog['type'] = 'info') => {
    storeAddLog({ timestamp: new Date().toLocaleTimeString(), message: msg, type });
  }, [storeAddLog]);

  const uploadSingleFile = useCallback(async (file: File): Promise<'success' | 'skipped'> => {
    const formData = new FormData();
    formData.append('source_type', 'file');
    formData.append('file', file);

    const res = await fetch(`${CONFIG.RAG.BASE_URL}/knowledge-base/ingest`, {
      method: 'POST',
      body: formData,
    });

    if (!res.ok) throw new Error('Upload failed');
    if (!res.body) throw new Error('No response body');

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let finalStatus: 'success' | 'skipped' = 'success';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      buffer += chunk;

      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const update = JSON.parse(line);

          if (update.message) {
            setMessage(update.message);
            const logType = update.status === 'error' || update.phase === 'error' ? 'error' : update.status === 'skipped' ? 'warning' : 'info';
            addLog(update.message, logType);
          }

          const status = update.status || update.phase;
          if (['reading', 'analyzing', 'embedding'].includes(status)) {
            setCurrentStep(status as IngestionStep);
            // Track model name for each step
            if (update.model) {
              setStepModel(status as IngestionStep, update.model);
            }
          }

          if (status === 'skipped') {
            finalStatus = 'skipped';
          }

          if (update.total && update.total > 0) {
            let currentProgress = 0;
            if (typeof update.progress === 'number') {
              currentProgress = (update.progress / update.total) * 100;
            }
            setProgress(Math.min(Math.round(currentProgress), 99));
          } else if (typeof update.progress === 'number') {
            setProgress(Math.min(update.progress, 99));
          } else if (status === 'reading') {
            setProgress(10);
          } else if (status === 'analyzing') {
            setProgress(30);
          }

          if (status === 'complete') {
            setProgress(100);
            addLog(`Ingestion complete for ${file.name}. Chunks: ${update.chunks}`, 'success');
            finalStatus = 'success';
          }

          if (status === 'error') {
            throw new Error(update.message || 'Unknown backend error');
          }

        } catch (e) {
          if (e instanceof Error && e.message !== 'Failed to parse update:') throw e;
          console.warn('Failed to parse stream line:', line);
        }
      }
    }

    return finalStatus;
  }, [addLog, setMessage, setCurrentStep, setProgress, setStepModel]);

  // File Upload Queue Processor
  useEffect(() => {
    const processNext = async () => {
      if (processingFile) return;

      if (queue.length === 0) {
        if (completedHistory.length > 0 && uploadStatus === 'uploading') {
          setUploadStatus('batch_complete');
          setMessage('All files processed.');
          setCurrentStep('complete');
          setProgress(100);
          onComplete?.();
        }
        return;
      }

      const file = queue[0];
      setProcessingFile(file);
      setUploadStatus('uploading');
      setCurrentStep('reading');
      setProgress(0);
      setMessage(`Starting ingestion for ${file.name}...`);
      clearLogs();
      addLog(`Beginning processing of ${file.name}`);

      try {
        const resultStatus = await uploadSingleFile(file);
        addToCompletedHistory({
          fileName: file.name,
          status: resultStatus,
          timestamp: new Date().toLocaleTimeString(),
          details: resultStatus === 'skipped' ? 'Skipped (unsupported/empty)' : undefined
        });
      } catch (err: any) {
        console.error(err);
        addLog(`Failed to process ${file.name}: ${err.message || err}`, 'error');
        addToCompletedHistory({
          fileName: file.name,
          status: 'error',
          timestamp: new Date().toLocaleTimeString(),
          details: err.message
        });
      } finally {
        setQueue(prev => prev.slice(1));
        setProcessingFile(null);
      }
    };

    processNext();
  }, [queue, processingFile, completedHistory, uploadStatus, addLog, uploadSingleFile, onComplete, setUploadStatus, setMessage, setCurrentStep, setProgress, clearLogs, addToCompletedHistory]);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const newFiles = Array.from(e.target.files);
      setQueue(prev => [...prev, ...newFiles]);

      if (uploadStatus === 'idle' || uploadStatus === 'batch_complete') {
        setUploadStatus('uploading');
      }
    }
    e.target.value = '';
  }, [uploadStatus, setUploadStatus]);

  return {
    uploadStatus,
    currentStep,
    progress,
    message,
    queue,
    processingFile,
    completedHistory,
    logs,
    showLogs,
    setShowLogs,
    handleFileSelect,
    addLog,
    stepModels,
  };
}
