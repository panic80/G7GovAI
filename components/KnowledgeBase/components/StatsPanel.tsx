import React from 'react';
import { Upload, History, Globe, BarChart3 } from 'lucide-react';
import { useLanguage } from '../../../contexts/LanguageContext';
import type { KnowledgeBaseStats } from '../types';

interface StatsPanelProps {
  stats: KnowledgeBaseStats;
}

export const StatsPanel: React.FC<StatsPanelProps> = ({ stats }) => {
  const { t } = useLanguage();

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6 shadow-sm">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-blue-50 rounded-lg">
            <BarChart3 className="text-gov-blue" size={24} />
          </div>
          <div>
            <p className="text-sm text-gray-500">{t('kb.stats.total')}</p>
            <p className="text-2xl font-bold text-gray-900">{stats.total_documents.toLocaleString()}</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="p-3 bg-green-50 rounded-lg">
            <Upload className="text-green-600" size={24} />
          </div>
          <div>
            <p className="text-sm text-gray-500">{t('kb.stats.upload')}</p>
            <p className="text-2xl font-bold text-gray-900">{(stats.by_connector.file_upload || 0).toLocaleString()}</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="p-3 bg-purple-50 rounded-lg">
            <Globe className="text-purple-600" size={24} />
          </div>
          <div>
            <p className="text-sm text-gray-500">{t('kb.stats.g7')}</p>
            <p className="text-2xl font-bold text-gray-900">
              {Object.entries(stats.by_connector)
                .filter(([k]) => k !== 'file_upload')
                .reduce((acc, [, v]) => acc + v, 0)
                .toLocaleString()}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="p-3 bg-orange-50 rounded-lg">
            <History className="text-orange-600" size={24} />
          </div>
          <div>
            <p className="text-sm text-gray-500">{t('kb.stats.updated')}</p>
            <p className="text-lg font-semibold text-gray-900">{stats.last_updated || 'N/A'}</p>
          </div>
        </div>
      </div>
    </div>
  );
};
