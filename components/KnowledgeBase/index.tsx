import React, { useState, useEffect, useRef } from 'react';
import { useLanguage } from '../../contexts/LanguageContext';

// Hooks
import { useStats, useFileUpload, useSampleData, useConnectors, useSources } from './hooks';

// Components
import { Header, StatsPanel, TabBar, FileUploadTab, ConnectorsTab, SourcesTab } from './components';

type TabType = 'upload' | 'connectors' | 'sources';

export const KnowledgeBase: React.FC = () => {
  const { t } = useLanguage();

  // Tab state
  const [activeTab, setActiveTab] = useState<TabType>('upload');

  // Stats hook
  const {
    stats,
    statsLoading,
    purging,
    fetchStats,
    purgeDatabase,
  } = useStats();

  // File upload hook
  const {
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
  } = useFileUpload({ onComplete: fetchStats });

  // Sample data hook
  const {
    loading: sampleDataLoading,
    progress: sampleDataProgress,
    files: sampleDataFiles,
    listRef: sampleDataListRef,
    loadSampleData,
  } = useSampleData({ onComplete: fetchStats });

  // Connectors hook
  const {
    connectors,
    loading: connectorsLoading,
    selectedConnector,
    datasets,
    datasetsLoading,
    importProgress,
    expandedCountry,
    fetchConnectors,
    fetchDatasets,
    handleImportDataset,
    toggleCountry,
  } = useConnectors({ onImportComplete: fetchStats });

  // Sources hook
  const {
    sources,
    loading: sourcesLoading,
    refresh: refreshSources,
  } = useSources();

  // Fetch stats and connectors on mount
  useEffect(() => {
    fetchStats();
    fetchConnectors();
  }, [fetchStats, fetchConnectors]);

  // Handle sample data loading
  const handleLoadSampleData = () => {
    loadSampleData(t('kb.loadSampleData.confirm'), addLog);
  };

  // Handle purge
  const handlePurge = () => {
    purgeDatabase(addLog);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <Header
        stats={stats}
        statsLoading={statsLoading}
        purging={purging}
        sampleDataProgress={sampleDataProgress}
        sampleDataFiles={sampleDataFiles}
        sampleDataListRef={sampleDataListRef}
        onRefreshStats={fetchStats}
        onPurge={handlePurge}
      />

      <div className="p-8">
        {/* Stats Banner */}
        {stats && <StatsPanel stats={stats} />}

        {/* Tab Bar */}
        <TabBar
          activeTab={activeTab}
          onTabChange={setActiveTab}
          sampleDataLoading={sampleDataLoading}
          onLoadSampleData={handleLoadSampleData}
        />

        {/* Upload Tab */}
        {activeTab === 'upload' && (
          <FileUploadTab
            uploadStatus={uploadStatus}
            currentStep={currentStep}
            progress={progress}
            message={message}
            queue={queue}
            processingFile={processingFile}
            completedHistory={completedHistory}
            logs={logs}
            showLogs={showLogs}
            onToggleLogs={() => setShowLogs(!showLogs)}
            onFileSelect={handleFileSelect}
            stepModels={stepModels}
          />
        )}

        {/* Connectors Tab */}
        {activeTab === 'connectors' && (
          <ConnectorsTab
            connectors={connectors}
            connectorsLoading={connectorsLoading}
            expandedCountry={expandedCountry}
            selectedConnector={selectedConnector}
            datasets={datasets}
            datasetsLoading={datasetsLoading}
            importProgress={importProgress}
            onToggleCountry={toggleCountry}
            onSelectConnector={fetchDatasets}
            onImportDataset={handleImportDataset}
          />
        )}

        {/* Sources Tab */}
        {activeTab === 'sources' && (
          <SourcesTab
            sources={sources}
            loading={sourcesLoading}
            onRefresh={refreshSources}
          />
        )}
      </div>
    </div>
  );
};

export default KnowledgeBase;
