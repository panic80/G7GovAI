import { useState, useEffect, useCallback } from 'react';
import { CONFIG } from '../../../config';

interface DocumentSource {
  source_title: string;
  source_id: string;
  doc_type: string;
  category: string;
  themes: string;
  chunk_count: number;
  updated_at: string;
}

export function useSources() {
  const [sources, setSources] = useState<DocumentSource[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSources = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${CONFIG.RAG.BASE_URL}/documents`);
      if (!res.ok) {
        throw new Error('Failed to fetch sources');
      }
      const data = await res.json();
      setSources(data);
    } catch (err) {
      console.error('Error fetching sources:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSources();
  }, [fetchSources]);

  return {
    sources,
    loading,
    error,
    refresh: fetchSources,
  };
}
