import React from 'react';
import { Database, RefreshCw, Trash2, Loader2 } from 'lucide-react';
import { useLanguage } from '../../../contexts/LanguageContext';
import type { KnowledgeBaseStats, SampleDataProgressState, SampleDataFile } from '../types';
import { SampleDataProgress } from './SampleDataProgress';

interface HeaderProps {
  stats: KnowledgeBaseStats | null;
  statsLoading: boolean;
  purging: boolean;
  sampleDataProgress: SampleDataProgressState | null;
  sampleDataFiles: SampleDataFile[];
  sampleDataListRef: React.RefObject<HTMLDivElement>;
  onRefreshStats: () => void;
  onPurge: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  stats,
  statsLoading,
  purging,
  sampleDataProgress,
  sampleDataFiles,
  sampleDataListRef,
  onRefreshStats,
  onPurge,
}) => {
  const { t } = useLanguage();

  return (
    <header className="bg-white border-b border-gray-200 px-8 py-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
            <Database className="text-gov-blue" />
            {t('kb.title')}
          </h1>
          <p className="text-gray-500 mt-1">{t('kb.subtitle')}</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onRefreshStats}
            className="flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm font-medium transition"
          >
            <RefreshCw size={16} className={statsLoading ? 'animate-spin' : ''} />
            {t('kb.refreshStats')}
          </button>
          <button
            onClick={onPurge}
            disabled={purging || !stats?.total_documents}
            className="flex items-center gap-2 px-4 py-2 bg-red-50 hover:bg-red-100 text-red-700 rounded-lg text-sm font-medium transition border border-red-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {purging ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Trash2 size={16} />
            )}
            {purging ? 'Purging...' : 'Purge Database'}
          </button>
        </div>
      </div>

      {/* Sample Data Progress Panel */}
      {sampleDataProgress && (
        <SampleDataProgress
          progress={sampleDataProgress}
          files={sampleDataFiles}
          listRef={sampleDataListRef}
        />
      )}
    </header>
  );
};
