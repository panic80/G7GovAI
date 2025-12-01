import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { BookOpen, ChevronDown, ChevronUp, FileText, MapPin, ExternalLink } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';
import { RagResponse } from '../types';

interface GovLensCitationsProps {
  citations: RagResponse['citations'];
  highlightedCitation?: number | null;
}

export const GovLensCitations: React.FC<GovLensCitationsProps> = ({ citations, highlightedCitation }) => {
  const { t } = useLanguage();
  const [isOpen, setIsOpen] = useState(true);
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);

  const handleCardClick = (idx: number, e: React.MouseEvent) => {
    // Don't toggle if clicking on the View Document link
    if ((e.target as HTMLElement).closest('a')) return;
    setExpandedIdx(expandedIdx === idx ? null : idx);
  };

  return (
    <div className="bg-gray-50 rounded-xl border border-gray-200 h-fit transition-all duration-200">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-6 hover:bg-gray-100 transition-colors rounded-t-xl focus:outline-none"
      >
        <div className="flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-gov-blue" />
          <h3 className="text-lg font-semibold text-gray-900">{t('govlens.sources')}</h3>
          <span className="ml-2 text-xs bg-gray-200 text-gray-700 px-2 py-0.5 rounded-full">
            {citations.length}
          </span>
        </div>
        {isOpen ? (
          <ChevronUp className="w-5 h-5 text-gray-500" />
        ) : (
          <ChevronDown className="w-5 h-5 text-gray-500" />
        )}
      </button>

      {isOpen && (
        <div className="px-6 pb-6 space-y-3 border-t border-gray-200 pt-4">
          {citations.length === 0 ? (
            <p className="text-sm text-gray-500">{t('govlens.no_sources')}</p>
          ) : (
            citations.map((cit, idx) => {
              const isExpanded = expandedIdx === idx;
              return (
                <div
                  key={cit.doc_id || `citation-${idx}`}
                  id={`citation-${idx + 1}`}
                  onClick={(e) => handleCardClick(idx, e)}
                  className={`p-3 bg-white rounded border transition-all duration-200 cursor-pointer group ${
                    highlightedCitation === idx + 1
                      ? 'border-gov-blue ring-2 ring-gov-blue ring-opacity-50 bg-blue-50'
                      : isExpanded
                        ? 'border-gov-blue bg-blue-50/30'
                        : 'border-gray-200 hover:border-gov-blue'
                  }`}
                  title={isExpanded ? undefined : cit.doc_id}
                >
                  {/* Header row */}
                  <div className="flex justify-between items-start mb-1">
                    <div className="flex items-center gap-2">
                      <span className="inline-flex items-center justify-center w-5 h-5 text-[10px] font-bold rounded-full bg-blue-100 text-gov-blue shrink-0">
                        {idx + 1}
                      </span>
                      <span className="text-sm font-bold text-gov-blue group-hover:underline">
                        {cit.title || cit.doc_id}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {cit.category && (
                        <span className="bg-gray-100 text-gray-600 text-[10px] px-2 py-0.5 rounded-full uppercase tracking-wide font-medium">
                          {cit.category}
                        </span>
                      )}
                      <ChevronDown
                        className={`w-4 h-4 text-gray-400 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
                      />
                    </div>
                  </div>

                  {/* Snippet - truncated when collapsed, full when expanded */}
                  <div className={`text-xs text-gray-600 break-words transition-all duration-200 ${
                    isExpanded ? '' : 'line-clamp-3'
                  }`}>
                    {cit.snippet || cit.locator}
                  </div>

                  {/* Expanded content */}
                  {isExpanded && (
                    <div className="mt-3 pt-3 border-t border-gray-200 space-y-2 animate-fadeIn">
                      {/* Metadata */}
                      <div className="flex flex-col gap-1.5 text-xs text-gray-500">
                        <div className="flex items-center gap-1.5">
                          <FileText className="w-3.5 h-3.5" />
                          <span className="font-medium">Doc ID:</span>
                          <span className="text-gray-700 font-mono text-[11px]">{cit.doc_id}</span>
                        </div>
                        {cit.locator && cit.locator !== cit.snippet && (
                          <div className="flex items-center gap-1.5">
                            <MapPin className="w-3.5 h-3.5" />
                            <span className="font-medium">Location:</span>
                            <span className="text-gray-700">{cit.locator}</span>
                          </div>
                        )}
                      </div>

                      {/* View Document Link */}
                      <Link
                        to={`/documents/${encodeURIComponent(cit.doc_id)}`}
                        className="inline-flex items-center gap-1.5 mt-2 px-3 py-1.5 bg-gov-blue text-white text-xs font-medium rounded hover:bg-blue-700 transition-colors"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                        View Full Document
                      </Link>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
};
