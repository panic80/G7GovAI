import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { FileText, Calendar, Tag, ChevronDown, MapPin, ExternalLink } from 'lucide-react';
import { KnowledgeChunk } from '../types';

interface SemanticSearchCitationsProps {
  results: KnowledgeChunk[];
}

export const SemanticSearchCitations: React.FC<SemanticSearchCitationsProps> = ({ results }) => {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);

  const handleCardClick = (idx: number, e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest('a')) return;
    setExpandedIdx(expandedIdx === idx ? null : idx);
  };

  const getMatchQuality = (score: number) => {
    const percentage = score * 100;
    if (percentage >= 30) return { label: 'Exact', color: 'text-emerald-700 bg-emerald-50 border-emerald-200' };
    if (percentage >= 15) return { label: 'High', color: 'text-green-700 bg-green-50 border-green-200' };
    if (percentage >= 5) return { label: 'Medium', color: 'text-yellow-700 bg-yellow-50 border-yellow-200' };
    return { label: 'Low', color: 'text-gray-600 bg-gray-50 border-gray-200' };
  };

  if (!results || results.length === 0) {
    return (
      <div className="bg-gray-50 rounded-xl border border-gray-200 p-6">
        <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-4 flex items-center gap-2">
          <FileText size={16} className="text-gov-blue" />
          Sources
        </h3>
        <div className="text-gray-500 italic">No semantic matches found.</div>
      </div>
    );
  }

  return (
    <div className="bg-gray-50 rounded-xl border border-gray-200 h-fit">
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider flex items-center gap-2">
          <FileText size={16} className="text-gov-blue" />
          Sources
          <span className="ml-auto text-xs font-normal text-gray-500 bg-gray-200 px-2 py-0.5 rounded-full">
            {results.length}
          </span>
        </h3>
      </div>

      {/* Scrollable citations list */}
      <div className="p-3 max-h-[600px] overflow-y-auto space-y-2">
        {results.map((chunk, idx) => {
          const quality = getMatchQuality(chunk.score);
          const isExpanded = expandedIdx === idx;

          return (
            <div
              key={chunk.id}
              id={`semantic-source-${idx + 1}`}
              onClick={(e) => handleCardClick(idx, e)}
              className={`p-3 bg-white rounded border transition-all duration-200 cursor-pointer group ${
                isExpanded
                  ? 'border-gov-blue bg-blue-50/30'
                  : 'border-gray-200 hover:border-gov-blue'
              }`}
            >
              {/* Header row */}
              <div className="flex justify-between items-start mb-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="flex items-center justify-center w-5 h-5 text-[10px] font-bold bg-gov-blue text-white rounded-full shrink-0">
                      {idx + 1}
                    </span>
                    <h4 className="font-medium text-sm text-gov-blue group-hover:underline truncate">
                      {chunk.source_title || 'Unknown Source'}
                    </h4>
                  </div>
                  <div className="flex flex-wrap items-center gap-1.5 text-[10px] text-gray-500 mt-1.5 ml-7">
                    <span className="bg-gray-100 px-1.5 py-0.5 rounded uppercase tracking-wide font-medium">
                      {chunk.doc_type || 'DOC'}
                    </span>
                    {chunk.category && (
                      <span className="flex items-center gap-0.5">
                        <Tag size={8} />
                        {chunk.category}
                      </span>
                    )}
                    {chunk.effective_date_start && (
                      <span className="flex items-center gap-0.5">
                        <Calendar size={8} />
                        {chunk.effective_date_start}
                      </span>
                    )}
                    <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold border ${quality.color}`}>
                      {quality.label} ({(chunk.score * 100).toFixed(0)}%)
                    </span>
                  </div>
                </div>
                <ChevronDown
                  className={`w-4 h-4 text-gray-400 transition-transform duration-200 shrink-0 ml-2 ${
                    isExpanded ? 'rotate-180' : ''
                  }`}
                />
              </div>

              {/* Content preview */}
              <div className={`text-xs text-gray-700 leading-relaxed whitespace-pre-wrap ml-7 ${
                isExpanded ? '' : 'line-clamp-2'
              }`}>
                {chunk.content}
              </div>

              {/* Expanded content */}
              {isExpanded && (
                <div className="mt-3 pt-3 border-t border-gray-200 ml-7 space-y-2 animate-fadeIn">
                  {/* Metadata */}
                  <div className="flex flex-col gap-1 text-[10px] text-gray-500">
                    <div className="flex items-center gap-1">
                      <FileText className="w-3 h-3" />
                      <span className="font-medium">Source ID:</span>
                      <span className="text-gray-700 font-mono">{chunk.source_id}</span>
                    </div>
                    {chunk.section_reference && (
                      <div className="flex items-center gap-1">
                        <MapPin className="w-3 h-3" />
                        <span className="font-medium">Section:</span>
                        <span className="text-gray-700">{chunk.section_reference}</span>
                      </div>
                    )}
                  </div>

                  {/* Themes */}
                  {chunk.themes && (
                    <div className="flex flex-wrap gap-1">
                      {chunk.themes.split(',').map((theme, i) => (
                        <span key={i} className="text-[9px] bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded-full">
                          {theme.trim()}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* View Document Link */}
                  <Link
                    to={`/documents/${encodeURIComponent(chunk.source_id)}`}
                    className="inline-flex items-center gap-1 mt-1 px-2 py-1 bg-gov-blue text-white text-[10px] font-medium rounded hover:bg-blue-700 transition-colors"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <ExternalLink className="w-3 h-3" />
                    View Full Document
                  </Link>
                </div>
              )}

              {/* Themes preview when collapsed */}
              {!isExpanded && chunk.themes && (
                <div className="mt-1.5 ml-7 flex flex-wrap gap-1">
                  {chunk.themes.split(',').slice(0, 2).map((theme, i) => (
                    <span key={i} className="text-[9px] bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded-full">
                      {theme.trim()}
                    </span>
                  ))}
                  {chunk.themes.split(',').length > 2 && (
                    <span className="text-[9px] text-gray-400">
                      +{chunk.themes.split(',').length - 2}
                    </span>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
