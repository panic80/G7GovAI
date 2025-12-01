import React, { useState, useCallback } from 'react';
import { SearchResult } from '../types';
import { GovLensAnswer } from './GovLensAnswer';
import { GovLensCitations } from './GovLensCitations';
import { SemanticSearchResults } from './SemanticSearchResults';
import { CITATION_HIGHLIGHT_MS } from '../constants';

interface GovLensResultsProps {
  result: SearchResult;
}

export const GovLensResults: React.FC<GovLensResultsProps> = ({ result }) => {
  const [highlightedCitation, setHighlightedCitation] = useState<number | null>(null);

  const handleCitationClick = useCallback((citationNumber: number) => {
    // Scroll to the citation in the citations panel
    const element = document.getElementById(`citation-${citationNumber}`);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' });
      setHighlightedCitation(citationNumber);
      // Clear highlight after animation
      setTimeout(() => setHighlightedCitation(null), CITATION_HIGHLIGHT_MS);
    }
  }, []);

  if (result.type === 'semantic') {
      return (
        <div className="animate-resultReveal">
          <SemanticSearchResults results={result.results} />
        </div>
      );
  }

  // Default: RAG View
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 animate-resultReveal">
      {/* Main Answer Column */}
      <div className="lg:col-span-2 space-y-6">
        <GovLensAnswer result={result} onCitationClick={handleCitationClick} />
      </div>

      {/* Citations Column */}
      <div className="space-y-6 animate-slideInUp" style={{ animationDelay: '0.2s' }}>
        <GovLensCitations citations={result.citations} highlightedCitation={highlightedCitation} />
      </div>
    </div>
  );
};