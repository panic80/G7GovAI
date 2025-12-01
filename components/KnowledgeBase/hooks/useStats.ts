import { useCallback } from 'react';
import { CONFIG } from '../../../config';
import { useKnowledgeBaseStore } from '../../../stores/knowledgeBaseStore';
import type { KnowledgeBaseStats } from '../types';

export function useStats() {
  const {
    stats,
    setStats,
    statsLoading,
    setStatsLoading,
    purging,
    setPurging,
  } = useKnowledgeBaseStore();

  const fetchStats = useCallback(async () => {
    setStatsLoading(true);
    try {
      const response = await fetch(`${CONFIG.RAG.BASE_URL}/knowledge-base/stats`);
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Error fetching stats:', error);
    } finally {
      setStatsLoading(false);
    }
  }, [setStats, setStatsLoading]);

  const purgeDatabase = useCallback(async (addLog: (msg: string, type: 'info' | 'error' | 'success' | 'warning') => void) => {
    const docCount = stats?.total_documents || 0;
    const confirmed = window.confirm(
      `Warning: This will permanently delete all ${docCount.toLocaleString()} documents from the knowledge base.\n\nThis action cannot be undone.\n\nAre you sure you want to continue?`
    );
    if (!confirmed) return;

    const doubleConfirmed = window.confirm(
      `Final confirmation: Delete ALL data from the knowledge base?`
    );
    if (!doubleConfirmed) return;

    setPurging(true);
    addLog('Purging knowledge base...', 'warning');

    try {
      const response = await fetch(`${CONFIG.RAG.BASE_URL}/knowledge-base/purge?confirmation=CONFIRM_PURGE_ALL_DATA`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error(`HTTP error: ${response.status}`);
      }

      const data = await response.json();
      addLog(`Purge complete: ${data.message}`, 'success');
      await fetchStats();
    } catch (error) {
      console.error('Error purging database:', error);
      addLog(`Failed to purge database: ${error}`, 'error');
    } finally {
      setPurging(false);
    }
  }, [stats, fetchStats, setPurging]);

  return {
    stats,
    statsLoading,
    purging,
    fetchStats,
    purgeDatabase,
  };
}
