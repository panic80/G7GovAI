import { useCallback } from 'react';
import { CONFIG } from '../../../config';
import { TOAST_DURATION_MS } from '../../../constants';
import { streamJsonLinesFromResponse } from '../../../services/apiClient';
import { useKnowledgeBaseStore } from '../../../stores/knowledgeBaseStore';

interface UseConnectorsOptions {
  onImportComplete?: () => void;
}

interface ConnectorImportUpdate {
  phase?: string;
  status?: string;
  progress?: number;
  message?: string;
}

export function useConnectors(options: UseConnectorsOptions = {}) {
  const { onImportComplete } = options;

  const {
    connectors,
    setConnectors,
    connectorsLoading: loading,
    setConnectorsLoading: setLoading,
    selectedConnector,
    setSelectedConnector,
    datasets,
    setDatasets,
    datasetsLoading,
    setDatasetsLoading,
    importProgress,
    setImportProgress,
    expandedCountry,
    setExpandedCountry,
    toggleCountry,
  } = useKnowledgeBaseStore();

  const fetchConnectors = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(`${CONFIG.RAG.BASE_URL}/knowledge-base/connectors`);
      if (response.ok) {
        const data = await response.json();
        setConnectors(data.connectors || {});
      }
    } catch (error) {
      console.error('Error fetching connectors:', error);
    } finally {
      setLoading(false);
    }
  }, [setLoading, setConnectors]);

  const fetchDatasets = useCallback(async (connectorId: string) => {
    setSelectedConnector(connectorId);
    setDatasetsLoading(true);
    setDatasets([]);
    try {
      const response = await fetch(`${CONFIG.RAG.BASE_URL}/knowledge-base/connectors/${connectorId}/datasets`);
      if (response.ok) {
        const data = await response.json();
        setDatasets(data.datasets || []);
      }
    } catch (error) {
      console.error('Error fetching datasets:', error);
    } finally {
      setDatasetsLoading(false);
    }
  }, [setSelectedConnector, setDatasetsLoading, setDatasets]);

  const handleImportDataset = useCallback(async (connectorId: string, datasetId: string) => {
    setImportProgress({ phase: 'starting', progress: 0, message: 'Connecting...' });

    try {
      const formData = new FormData();
      formData.append('source_type', 'connector');
      formData.append('connector_id', connectorId);
      formData.append('dataset_id', datasetId);

      const res = await fetch(`${CONFIG.RAG.BASE_URL}/knowledge-base/ingest`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) throw new Error('Import failed');
      if (!res.body) throw new Error('No response body');

      for await (const update of streamJsonLinesFromResponse<ConnectorImportUpdate>(res)) {
        setImportProgress({
          phase: update.phase || update.status || 'processing',
          progress: update.progress || 0,
          message: update.message || 'Processing...'
        });

        if (update.phase === 'complete' || update.status === 'complete') {
          setTimeout(() => {
            setImportProgress(null);
            onImportComplete?.();
          }, 2000);
        }
      }
    } catch (error: any) {
      setImportProgress({
        phase: 'error',
        progress: 0,
        message: error.message || 'Import failed'
      });
      setTimeout(() => setImportProgress(null), TOAST_DURATION_MS);
    }
  }, [onImportComplete, setImportProgress]);

  return {
    connectors,
    loading,
    selectedConnector,
    datasets,
    datasetsLoading,
    importProgress,
    expandedCountry,
    fetchConnectors,
    fetchDatasets,
    handleImportDataset,
    toggleCountry,
  };
}
