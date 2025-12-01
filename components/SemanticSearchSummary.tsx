import React from 'react';
import { Sparkles, Loader2 } from 'lucide-react';
import { MarkdownRenderer } from './MarkdownRenderer';

interface SemanticSearchSummaryProps {
  summary: string | null;
  isLoading: boolean;
}

export const SemanticSearchSummary: React.FC<SemanticSearchSummaryProps> = ({
  summary,
  isLoading,
}) => {
  return (
    <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
      <h3 className="text-sm font-bold text-purple-800 uppercase tracking-wider mb-4 flex items-center gap-2">
        <Sparkles size={16} className="text-purple-600" />
        Summary
      </h3>

      {isLoading && (
        <div className="flex items-center gap-3 text-purple-600">
          <Loader2 className="w-5 h-5 animate-spin" />
          <span className="font-medium">Synthesizing results...</span>
        </div>
      )}

      {!isLoading && summary && (
        <div className="text-gray-800 leading-relaxed prose prose-sm max-w-none">
          <MarkdownRenderer content={summary} />
        </div>
      )}

      {!isLoading && !summary && (
        <div className="text-gray-500 italic">
          No summary available yet.
        </div>
      )}
    </div>
  );
};
