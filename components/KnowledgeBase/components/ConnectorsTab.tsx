import React from 'react';
import {
  Loader2,
  Globe,
  Database,
  ChevronDown,
  ChevronUp,
  CheckCircle,
  AlertCircle,
  History,
  Download,
} from 'lucide-react';
import { useLanguage } from '../../../contexts/LanguageContext';
import { COUNTRY_FLAGS, COUNTRY_NAMES } from '../../../constants';
import type { Connector, Dataset, ImportProgressState } from '../types';

interface ConnectorsTabProps {
  connectors: Record<string, Connector[]>;
  connectorsLoading: boolean;
  expandedCountry: string | null;
  selectedConnector: string | null;
  datasets: Dataset[];
  datasetsLoading: boolean;
  importProgress: ImportProgressState | null;
  onToggleCountry: (country: string) => void;
  onSelectConnector: (connectorId: string) => void;
  onImportDataset: (connectorId: string, datasetId: string) => void;
}

export const ConnectorsTab: React.FC<ConnectorsTabProps> = ({
  connectors,
  connectorsLoading,
  expandedCountry,
  selectedConnector,
  datasets,
  datasetsLoading,
  importProgress,
  onToggleCountry,
  onSelectConnector,
  onImportDataset,
}) => {
  const { t } = useLanguage();

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Countries List */}
      <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
        <div className="p-4 border-b border-gray-100 bg-gray-50">
          <h3 className="font-semibold text-gray-900 flex items-center gap-2">
            <Globe size={18} className="text-gov-blue" />
            {t('kb.connectors.title')}
          </h3>
          <p className="text-xs text-gray-500 mt-1">{t('kb.connectors.subtitle')}</p>
        </div>

        {connectorsLoading ? (
          <div className="p-8 flex items-center justify-center">
            <Loader2 className="animate-spin text-gov-blue" size={24} />
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {Object.entries(connectors).map(([country, countryConnectors]) => (
              <div key={country} className="border-b border-gray-100 last:border-b-0">
                <button
                  onClick={() => onToggleCountry(country)}
                  className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{COUNTRY_FLAGS[country] || '🌐'}</span>
                    <div className="text-left">
                      <p className="font-medium text-gray-900">{COUNTRY_NAMES[country] || country}</p>
                      <p className="text-xs text-gray-500">{countryConnectors.length} {t('kb.dataSources')}</p>
                    </div>
                  </div>
                  {expandedCountry === country ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                </button>

                {expandedCountry === country && (
                  <div className="bg-gray-50 px-4 pb-4">
                    {countryConnectors.map((connector) => (
                      <button
                        key={connector.id}
                        onClick={() => onSelectConnector(connector.id)}
                        className={`w-full text-left p-3 rounded-lg mb-2 transition ${
                          selectedConnector === connector.id
                            ? 'bg-gov-blue text-white'
                            : 'bg-white border border-gray-200 hover:border-gov-blue'
                        }`}
                      >
                        <p className="font-medium text-sm">{connector.name}</p>
                        <p className={`text-xs mt-1 ${selectedConnector === connector.id ? 'text-blue-100' : 'text-gray-500'}`}>
                          {connector.description}
                        </p>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Datasets Panel */}
      <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
        <div className="p-4 border-b border-gray-100 bg-gray-50">
          <h3 className="font-semibold text-gray-900 flex items-center gap-2">
            <Database size={18} className="text-gov-blue" />
            {t('kb.datasets.title')}
          </h3>
          <p className="text-xs text-gray-500 mt-1">
            {selectedConnector ? `${t('kb.datasets.from')} ${selectedConnector.toUpperCase()}` : t('kb.datasets.select')}
          </p>
        </div>

        {/* Import Progress */}
        {importProgress && (
          <div className="p-4 bg-blue-50 border-b border-blue-100">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-3">
                {importProgress.phase === 'error' ? (
                  <AlertCircle className="text-red-500" size={20} />
                ) : importProgress.phase === 'complete' ? (
                  <CheckCircle className="text-green-500" size={20} />
                ) : (
                  <Loader2 className="animate-spin text-gov-blue" size={20} />
                )}
                <div>
                  <span className="text-sm font-medium">{importProgress.message}</span>
                  {importProgress.phase !== 'complete' && importProgress.phase !== 'error' && (
                    <span className="text-xs text-gray-500 ml-2">
                      {importProgress.phase === 'starting' && `(${t('kb.phase.connecting')})`}
                      {importProgress.phase === 'processing' && `(${t('kb.phase.fetching')})`}
                      {importProgress.phase === 'fetched' && `(${t('kb.phase.received')})`}
                      {importProgress.phase === 'reading' && `(${t('kb.phase.processing')})`}
                      {importProgress.phase === 'converting' && `(${t('kb.phase.converting')})`}
                      {importProgress.phase === 'analyzing' && `(${t('kb.phase.analyzing')})`}
                      {importProgress.phase === 'embedding' && `(${t('kb.phase.storing')})`}
                    </span>
                  )}
                </div>
              </div>
              <span className="text-sm font-bold text-gov-blue">
                {importProgress.progress || 0}%
              </span>
            </div>
            <div className="w-full h-3 bg-blue-100 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-300 ${
                  importProgress.phase === 'error' ? 'bg-red-500' :
                    importProgress.phase === 'complete' ? 'bg-green-500' : 'bg-gov-blue'
                }`}
                style={{ width: `${importProgress.progress || 0}%` }}
              />
            </div>
          </div>
        )}

        {!selectedConnector ? (
          <div className="p-8 text-center text-gray-500">
            <Globe size={48} className="mx-auto mb-4 opacity-30" />
            <p>{t('kb.datasets.selectSource')}</p>
          </div>
        ) : datasetsLoading ? (
          <div className="p-8 text-center text-gray-500">
            <Loader2 className="animate-spin mx-auto mb-4 text-gov-blue" size={32} />
            <p className="font-medium">{t('kb.datasets.querying')} {selectedConnector.toUpperCase()} {t('kb.datasets.queryingData')}</p>
            <p className="text-xs mt-1">{t('kb.datasets.wait')}</p>
          </div>
        ) : datasets.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            <Database size={48} className="mx-auto mb-4 opacity-30" />
            <p>{t('kb.datasets.none')}</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100 max-h-[500px] overflow-y-auto">
            {datasets.map((dataset) => (
              <div key={dataset.id} className="p-4 hover:bg-gray-50 transition">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900 truncate">{dataset.name}</p>
                    <p className="text-xs text-gray-500 mt-1 line-clamp-2">{dataset.description}</p>
                    <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
                      <span className="flex items-center gap-1">
                        <Database size={12} />
                        ~{dataset.estimated_records.toLocaleString()} {t('kb.datasets.records')}
                      </span>
                      {dataset.last_updated && (
                        <span className="flex items-center gap-1">
                          <History size={12} />
                          {dataset.last_updated}
                        </span>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => onImportDataset(selectedConnector, dataset.id)}
                    disabled={!!importProgress}
                    className="ml-4 flex items-center gap-2 px-4 py-2 bg-gov-blue text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
                  >
                    <Download size={16} />
                    {t('btn.import')}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
