import React from 'react';
import { Upload, Globe, Sparkles, Loader2, Library } from 'lucide-react';
import { useLanguage } from '../../../contexts/LanguageContext';

type TabType = 'upload' | 'connectors' | 'sources';

interface TabBarProps {
  activeTab: TabType;
  onTabChange: (tab: TabType) => void;
  sampleDataLoading: boolean;
  onLoadSampleData: () => void;
}

export const TabBar: React.FC<TabBarProps> = ({
  activeTab,
  onTabChange,
  sampleDataLoading,
  onLoadSampleData,
}) => {
  const { t } = useLanguage();

  return (
    <div className="flex gap-2 mb-6">
      <button
        onClick={onLoadSampleData}
        disabled={sampleDataLoading}
        className="flex items-center gap-2 px-6 py-3 rounded-lg font-medium transition bg-emerald-100 hover:bg-emerald-200 text-emerald-700 border border-emerald-300 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {sampleDataLoading ? (
          <Loader2 size={18} className="animate-spin" />
        ) : (
          <Sparkles size={18} />
        )}
        {sampleDataLoading ? t('kb.loadSampleData.loading') : t('kb.loadSampleData')}
      </button>
      <button
        onClick={() => onTabChange('upload')}
        className={`flex items-center gap-2 px-6 py-3 rounded-lg font-medium transition ${
          activeTab === 'upload'
            ? 'bg-gov-blue text-white shadow-md'
            : 'bg-white text-gray-600 hover:bg-gray-100 border border-gray-200'
        }`}
      >
        <Upload size={18} />
        {t('kb.tab.upload')}
      </button>
      <button
        onClick={() => onTabChange('connectors')}
        className={`flex items-center gap-2 px-6 py-3 rounded-lg font-medium transition ${
          activeTab === 'connectors'
            ? 'bg-gov-blue text-white shadow-md'
            : 'bg-white text-gray-600 hover:bg-gray-100 border border-gray-200'
        }`}
      >
        <Globe size={18} />
        {t('kb.tab.connectors')}
      </button>
      <button
        onClick={() => onTabChange('sources')}
        className={`flex items-center gap-2 px-6 py-3 rounded-lg font-medium transition ${
          activeTab === 'sources'
            ? 'bg-gov-blue text-white shadow-md'
            : 'bg-white text-gray-600 hover:bg-gray-100 border border-gray-200'
        }`}
      >
        <Library size={18} />
        Sources
      </button>
    </div>
  );
};
