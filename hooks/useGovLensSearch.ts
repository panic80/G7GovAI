import React, { useEffect, useCallback } from 'react';
import { fetchFilterOptions } from '../services/ragService';
import { useLanguage } from '../contexts/LanguageContext';
import { useGovLensStore, SearchFilters, QAPair } from '../stores/govLensStore';

// Re-export types for backwards compatibility
export type { SearchFilters, QAPair };

export const useGovLensSearch = () => {
  const { language } = useLanguage();

  // Get state and actions from store
  const {
    query,
    setQuery,
    loading,
    currentQuery,
    results,
    streamingTrace,
    mode,
    setMode,
    selectedFilters,
    availableFilters,
    filtersLoading,
    setAvailableFilters,
    setFiltersLoading,
    updateFilters,
    clearFilters,
    clearResults,
    performSearch,
  } = useGovLensStore();

  // Check if any filters are active
  const hasActiveFilters = selectedFilters.categories.length > 0;

  // Fetch available filter options on mount (only if not already loaded)
  useEffect(() => {
    if (availableFilters.categories.length === 0) {
      const loadFilters = async () => {
        setFiltersLoading(true);
        try {
          const options = await fetchFilterOptions();
          setAvailableFilters(options);
        } catch (err) {
          console.error('Failed to load filter options:', err);
        } finally {
          setFiltersLoading(false);
        }
      };
      loadFilters();
    }
  }, [availableFilters.categories.length, setFiltersLoading, setAvailableFilters]);

  // No cleanup needed - streaming continues in background via store

  const handleSearch = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    // Delegate to store action - runs in background independent of component lifecycle
    performSearch(query, language);
  }, [query, language, performSearch]);

  return {
    query,
    setQuery,
    loading,
    currentQuery,
    results,
    streamingTrace,
    mode,
    setMode,
    handleSearch,
    clearResults,
    // Filter-related state and functions
    selectedFilters,
    availableFilters,
    filtersLoading,
    hasActiveFilters,
    updateFilters,
    clearFilters,
  };
};
