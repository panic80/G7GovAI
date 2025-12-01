import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { CONFIG } from '../config';

interface ApiKeyContextType {
  isConfigured: boolean;
  hasCustomKey: boolean;
  keyPreview: string | null;
  isLoading: boolean;
  refreshStatus: () => Promise<void>;
}

const ApiKeyContext = createContext<ApiKeyContextType | undefined>(undefined);

export const ApiKeyProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [isConfigured, setIsConfigured] = useState(true); // Assume configured initially to avoid flash
  const [hasCustomKey, setHasCustomKey] = useState(false);
  const [keyPreview, setKeyPreview] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${CONFIG.RAG.BASE_URL}/config/api-key`);
      if (res.ok) {
        const data = await res.json();
        setIsConfigured(data.api_key_configured);
        setHasCustomKey(data.has_custom_key);
        setKeyPreview(data.key_preview);
      }
    } catch (error) {
      if (import.meta.env.DEV) console.error('Failed to fetch API key status:', error);
      // On error, assume not configured to prompt user
      setIsConfigured(false);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  const refreshStatus = useCallback(async () => {
    await fetchStatus();
  }, [fetchStatus]);

  return (
    <ApiKeyContext.Provider value={{ isConfigured, hasCustomKey, keyPreview, isLoading, refreshStatus }}>
      {children}
    </ApiKeyContext.Provider>
  );
};

export const useApiKey = () => {
  const context = useContext(ApiKeyContext);
  if (!context) {
    throw new Error('useApiKey must be used within an ApiKeyProvider');
  }
  return context;
};
