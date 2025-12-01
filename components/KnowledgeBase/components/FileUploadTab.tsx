import React, { useRef, useEffect } from 'react';
import {
  Upload,
  CheckCircle,
  AlertCircle,
  Loader2,
  FileText,
  BrainCircuit,
  Database,
  ChevronDown,
  ChevronUp,
  Terminal,
  Plus,
  History,
  AlertTriangle,
} from 'lucide-react';
import { useLanguage } from '../../../contexts/LanguageContext';
import type { UploadHistoryItem, IngestionLog, UploadStatus, IngestionStep } from '../types';

interface FileUploadTabProps {
  uploadStatus: UploadStatus;
  currentStep: IngestionStep;
  progress: number;
  message: string;
  queue: File[];
  processingFile: File | null;
  completedHistory: UploadHistoryItem[];
  logs: IngestionLog[];
  showLogs: boolean;
  onToggleLogs: () => void;
  onFileSelect: (e: React.ChangeEvent<HTMLInputElement>) => void;
  stepModels?: Record<IngestionStep, string>;
}

const getStepIcon = (step: string) => {
  switch (step) {
    case 'reading': return <FileText size={18} />;
    case 'analyzing': return <BrainCircuit size={18} />;
    case 'embedding': return <Database size={18} />;
    default: return <Loader2 size={18} />;
  }
};

export const FileUploadTab: React.FC<FileUploadTabProps> = ({
  uploadStatus,
  currentStep,
  progress,
  message,
  queue,
  processingFile,
  completedHistory,
  logs,
  showLogs,
  onToggleLogs,
  onFileSelect,
  stepModels,
}) => {
  const { t } = useLanguage();
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (showLogs && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, showLogs]);

  const steps = [
    { id: 'reading', label: t('kb.steps.reading') },
    { id: 'analyzing', label: t('kb.steps.analyzing') },
    { id: 'embedding', label: t('kb.steps.embedding') }
  ];

  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
      <div className="p-6">
        {uploadStatus === 'idle' ? (
          <label className="flex flex-col items-center justify-center p-12 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:bg-gray-50 hover:border-gov-blue transition-colors group">
            <div className="p-4 bg-blue-50 rounded-full mb-4 group-hover:scale-110 transition-transform">
              <Upload className="text-gov-blue w-8 h-8" />
            </div>
            <span className="text-lg font-semibold text-gray-700">{t('kb.upload.title')}</span>
            <span className="text-sm text-gray-500 mt-2 text-center">
              {t('kb.upload.formats')}<br />
              <span className="text-xs text-gray-400">{t('kb.upload.multi')}</span>
            </span>
            <input type="file" className="hidden" onChange={onFileSelect} accept=".pdf,.txt,.md,.csv,.html,.json" multiple />
          </label>
        ) : (
          <div className="flex flex-col gap-4">
            {/* Status Header */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {uploadStatus === 'uploading' && <Loader2 className="animate-spin text-gov-blue" />}
                {uploadStatus === 'batch_complete' && <CheckCircle className="text-green-500" />}
                {uploadStatus === 'error' && <AlertCircle className="text-red-500" />}
                <div>
                  <h3 className="font-semibold text-gray-900">
                    {uploadStatus === 'batch_complete' ? t('kb.upload.complete') :
                      uploadStatus === 'error' ? t('kb.upload.failed') :
                        processingFile ? `${t('kb.upload.processing')} ${processingFile.name}` : t('kb.upload.preparing')}
                  </h3>
                  <p className="text-sm text-gray-500 truncate max-w-md">{message}</p>
                </div>
              </div>
              {uploadStatus === 'uploading' && (
                <span className="text-xl font-bold text-gov-blue">{progress}%</span>
              )}
            </div>

            {/* Progress Bar */}
            {uploadStatus === 'uploading' && (
              <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gov-blue transition-all duration-500 ease-out"
                  style={{ width: `${progress}%` }}
                />
              </div>
            )}

            {/* Steps */}
            {uploadStatus === 'uploading' && (
              <div className="grid grid-cols-3 gap-2 mt-2">
                {steps.map((s, i) => {
                  const isActive = currentStep === s.id;
                  const isCompleted = steps.findIndex(x => x.id === currentStep) > i;
                  const modelName = stepModels?.[s.id as IngestionStep] || '';
                  return (
                    <div key={s.id} className={`flex items-center gap-2 p-3 rounded-lg border ${
                      isActive ? 'border-gov-blue bg-blue-50 text-gov-blue' :
                        isCompleted ? 'border-green-200 bg-green-50 text-green-700' :
                          'border-gray-100 text-gray-400'
                    }`}>
                      {isCompleted ? <CheckCircle size={16} /> : getStepIcon(s.id)}
                      <div className="flex flex-col min-w-0">
                        <span className="text-sm font-medium">{s.label}</span>
                        {modelName && (
                          <span className={`text-xs truncate ${
                            isActive ? 'text-blue-500' :
                              isCompleted ? 'text-green-600' :
                                'text-gray-400'
                          }`}>{modelName}</span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Queue */}
            {queue.length > 0 && (
              <div className="mt-2 p-3 bg-gray-50 rounded-lg border border-gray-100 flex items-center gap-2">
                <div className="w-6 h-6 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-sm font-bold">
                  {queue.length}
                </div>
                <span className="text-sm text-gray-600">{t('kb.upload.queue')}</span>
              </div>
            )}

            {/* History */}
            {completedHistory.length > 0 && (
              <div className="mt-4">
                <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 flex items-center gap-1">
                  <History size={12} /> {t('kb.upload.history')}
                </h4>
                <div className="space-y-2 max-h-40 overflow-y-auto">
                  {completedHistory.map((item, idx) => (
                    <div key={idx} className="flex items-center justify-between p-2 bg-gray-50 border border-gray-100 rounded-lg text-sm">
                      <div className="flex items-center gap-2">
                        {item.status === 'success' && <CheckCircle size={14} className="text-green-500" />}
                        {item.status === 'error' && <AlertCircle size={14} className="text-red-500" />}
                        {item.status === 'skipped' && <AlertTriangle size={14} className="text-yellow-500" />}
                        <span className="truncate font-medium text-gray-700">{item.fileName}</span>
                      </div>
                      <span className="text-xs text-gray-400">{item.timestamp}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Upload Another */}
            {uploadStatus === 'batch_complete' && (
              <div className="mt-4 flex justify-center">
                <label className="flex items-center gap-2 px-6 py-3 bg-gov-blue text-white rounded-lg cursor-pointer hover:bg-blue-700 transition-colors font-medium">
                  <Plus size={18} />
                  {t('kb.upload.another')}
                  <input type="file" className="hidden" onChange={onFileSelect} accept=".pdf,.txt,.md,.csv,.html,.json" multiple />
                </label>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Logs */}
      {uploadStatus !== 'idle' && (
        <div className="border-t border-gray-100 bg-gray-50">
          <button
            onClick={onToggleLogs}
            className="w-full flex items-center justify-between p-3 text-xs font-medium text-gray-500 hover:text-gray-700 hover:bg-gray-100 transition-colors"
          >
            <span className="flex items-center gap-2">
              <Terminal size={14} />
              {showLogs ? t('kb.upload.hideLogs') : t('kb.upload.showLogs')}
            </span>
            {showLogs ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>

          {showLogs && (
            <div className="p-3 max-h-48 overflow-y-auto font-mono text-xs space-y-1 border-t border-gray-200 bg-slate-900 text-slate-300">
              {logs.map((log, i) => (
                <div key={i} className={`flex gap-2 ${
                  log.type === 'error' ? 'text-red-400' :
                    log.type === 'success' ? 'text-green-400' :
                      log.type === 'warning' ? 'text-yellow-400' : 'text-slate-300'
                }`}>
                  <span className="text-slate-500 select-none">[{log.timestamp}]</span>
                  <span>{log.message}</span>
                </div>
              ))}
              <div ref={logsEndRef} />
            </div>
          )}
        </div>
      )}
    </div>
  );
};
