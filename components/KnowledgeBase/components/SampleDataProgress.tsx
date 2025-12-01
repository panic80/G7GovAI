import React from 'react';
import { Loader2, CheckCircle, AlertCircle, BrainCircuit } from 'lucide-react';
import type { SampleDataProgressState, SampleDataFile } from '../types';

interface SampleDataProgressProps {
  progress: SampleDataProgressState;
  files: SampleDataFile[];
  listRef: React.RefObject<HTMLDivElement>;
}

export const SampleDataProgress: React.FC<SampleDataProgressProps> = ({ progress, files, listRef }) => {
  return (
    <div className="mt-4 bg-emerald-50 rounded-lg p-4 border border-emerald-200">
      {/* Header with progress */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Loader2 size={18} className="animate-spin text-emerald-600" />
          <span className="text-sm font-semibold text-emerald-800">
            {progress.fileIndex && progress.totalFiles
              ? `Processing file ${progress.fileIndex} of ${progress.totalFiles}`
              : 'Loading sample data...'}
          </span>
        </div>
        <span className="text-sm font-bold text-emerald-700 bg-emerald-100 px-2 py-1 rounded">
          {progress.progress}%
        </span>
      </div>

      {/* Progress bar */}
      <div className="w-full bg-emerald-200 rounded-full h-2.5 mb-4">
        <div
          className="bg-emerald-600 h-2.5 rounded-full transition-all duration-300"
          style={{ width: `${progress.progress}%` }}
        />
      </div>

      {/* Current status message and model */}
      <div className="flex items-center justify-between mb-3">
        <div className="text-xs text-emerald-700 font-medium">
          {progress.message}
        </div>
        {progress.model && (
          <div className="flex items-center gap-1.5 text-xs bg-emerald-100 text-emerald-800 px-2 py-1 rounded-full">
            <BrainCircuit size={12} />
            <span className="font-mono">{progress.model}</span>
          </div>
        )}
      </div>

      {/* File list */}
      {files.length > 0 && (
        <div
          ref={listRef}
          className="bg-white rounded-lg border border-emerald-100 divide-y divide-emerald-50 max-h-48 overflow-y-auto scroll-smooth"
        >
          {files.map((file, idx) => (
            <div key={idx} className="flex items-center gap-3 px-3 py-2">
              {/* Status icon */}
              <div className="flex-shrink-0">
                {file.status === 'complete' ? (
                  <CheckCircle size={16} className="text-emerald-500" />
                ) : file.status === 'error' ? (
                  <AlertCircle size={16} className="text-red-500" />
                ) : file.status === 'processing' ? (
                  <Loader2 size={16} className="animate-spin text-emerald-600" />
                ) : (
                  <div className="w-4 h-4 rounded-full border-2 border-gray-300" />
                )}
              </div>

              {/* File info */}
              <div className="flex-1 min-w-0">
                <p className={`text-sm font-medium truncate ${
                  file.status === 'processing' ? 'text-emerald-700' :
                  file.status === 'complete' ? 'text-gray-700' :
                  file.status === 'error' ? 'text-red-700' : 'text-gray-400'
                }`}>
                  {file.title}
                </p>
                <p className="text-xs text-gray-400 truncate">{file.name}</p>
              </div>

              {/* Phase badge */}
              {file.status === 'processing' && file.phase && (
                <span className="flex-shrink-0 text-xs px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 capitalize">
                  {file.phase === 'reading' ? 'Reading' :
                   file.phase === 'analyzing' ? 'Analyzing' :
                   file.phase === 'embedding' ? 'Storing' :
                   file.phase}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
