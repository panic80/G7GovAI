import React, { useState, useEffect, useRef } from 'react';
import { FileText } from 'lucide-react';
import { KnowledgeChunk } from '../types';
import { summarizeAllText } from '../services/geminiService';
import { SemanticSearchSummary } from './SemanticSearchSummary';
import { SemanticSearchCitations } from './SemanticSearchCitations';

interface SemanticSearchResultsProps {
  results: KnowledgeChunk[];
}

export const SemanticSearchResults: React.FC<SemanticSearchResultsProps> = ({ results }) => {
  // Global synthesis state
  const [globalSummary, setGlobalSummary] = useState<string | null>(null);
  const [isLoadingGlobal, setIsLoadingGlobal] = useState(false);
  const autoSummarizedRef = useRef<string | null>(null);

  // Auto-summarize when results change
  useEffect(() => {
    if (results && results.length > 0) {
      const resultsKey = results.map(r => r.id).join(',');

      if (autoSummarizedRef.current !== resultsKey) {
        autoSummarizedRef.current = resultsKey;
        setGlobalSummary(null);

        // Auto-trigger global summarization
        setIsLoadingGlobal(true);
        const allTexts = results.map(r => r.content);
        summarizeAllText(allTexts)
          .then(summary => setGlobalSummary(summary))
          .catch((err) => { if (import.meta.env.DEV) console.error('Summarization failed:', err); })
          .finally(() => setIsLoadingGlobal(false));
      }
    }
  }, [results]);

  if (!results || results.length === 0) {
    return (
      <div className="text-gray-500 italic flex items-center gap-2">
        <FileText className="w-5 h-5" />
        No semantic matches found.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
          <FileText className="text-gov-blue" />
          Semantic Search Results
          <span className="text-sm font-normal text-gray-500 ml-2">
            ({results.length} matches)
          </span>
        </h2>
      </div>

      {/* Two-column layout matching GovLens RAG */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column - Summary */}
        <div className="lg:col-span-2 space-y-6">
          <SemanticSearchSummary
            summary={globalSummary}
            isLoading={isLoadingGlobal}
          />
        </div>

        {/* Right Column - Citations */}
        <div className="space-y-6">
          <SemanticSearchCitations results={results} />
        </div>
      </div>
    </div>
  );
};
