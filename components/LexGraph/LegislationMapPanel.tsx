'use client';

import React, { useState } from 'react';
import { LegislationMap, LegislativeExcerpt } from '../../types';
import { Scale, BookMarked, BookOpen, ChevronDown, ChevronRight } from 'lucide-react';

interface LegislationMapPanelProps {
  legislationMap: LegislationMap | null;
  onExcerptClick: (excerpt: LegislativeExcerpt) => void;
}

interface ExcerptCardProps {
  excerpt: LegislativeExcerpt;
  onClick: () => void;
}

const ExcerptCard: React.FC<ExcerptCardProps> = ({ excerpt, onClick }) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden bg-white hover:shadow-sm transition-shadow">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-3 flex items-start gap-3 text-left hover:bg-gray-50"
      >
        {expanded ? (
          <ChevronDown className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
        ) : (
          <ChevronRight className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
        )}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900 truncate">{excerpt.act_name}</p>
          <p className="text-xs text-blue-600 font-mono mt-0.5">{excerpt.citation}</p>
        </div>
        {excerpt.confidence && (
          <span className={`flex-shrink-0 px-2 py-0.5 text-xs rounded ${
            excerpt.confidence === 'HIGH' ? 'bg-green-100 text-green-700' :
            excerpt.confidence === 'MEDIUM' ? 'bg-yellow-100 text-yellow-700' :
            'bg-gray-100 text-gray-700'
          }`}>
            {excerpt.confidence}
          </span>
        )}
      </button>

      {expanded && (
        <div className="px-4 pb-4 pt-2 border-t border-gray-100">
          {excerpt.section_title && (
            <p className="text-xs font-medium text-gray-500 mb-2">{excerpt.section_title}</p>
          )}
          <p className="text-sm text-gray-600 line-clamp-3 mb-3">
            {excerpt.plain_language || excerpt.text.slice(0, 200) + '...'}
          </p>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onClick();
            }}
            className="text-xs text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1"
          >
            <BookOpen className="w-3 h-3" />
            View Full Text
          </button>
        </div>
      )}
    </div>
  );
};

type TabType = 'primary' | 'related' | 'definitions';

export const LegislationMapPanel: React.FC<LegislationMapPanelProps> = ({ legislationMap, onExcerptClick }) => {
  const [activeTab, setActiveTab] = useState<TabType>('primary');

  if (!legislationMap) {
    return (
      <div className="p-4 text-center text-gray-500">
        <Scale className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No legislation mapped yet</p>
      </div>
    );
  }

  const tabs: { id: TabType; label: string; icon: React.ReactNode; count: number }[] = [
    { id: 'primary', label: 'Primary', icon: <Scale className="w-4 h-4" />, count: legislationMap.primary.length },
    { id: 'related', label: 'Related', icon: <BookMarked className="w-4 h-4" />, count: legislationMap.related.length },
    { id: 'definitions', label: 'Definitions', icon: <BookOpen className="w-4 h-4" />, count: legislationMap.definitions.length },
  ];

  const currentExcerpts = legislationMap[activeTab];

  return (
    <div className="bg-gray-50 rounded-lg border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 bg-white border-b border-gray-200">
        <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
          <Scale className="w-4 h-4 text-blue-600" />
          Relevant Legislation
        </h3>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200 bg-white">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex-1 px-3 py-2 text-xs font-medium flex items-center justify-center gap-1.5 transition-colors ${
              activeTab === tab.id
                ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50'
                : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
            }`}
          >
            {tab.icon}
            {tab.label}
            {tab.count > 0 && (
              <span className={`ml-1 px-1.5 py-0.5 rounded-full text-xs ${
                activeTab === tab.id ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'
              }`}>
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="p-3 space-y-2 max-h-[400px] overflow-y-auto">
        {currentExcerpts.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <p className="text-sm">No {activeTab} legislation found</p>
          </div>
        ) : (
          currentExcerpts.map((excerpt, index) => (
            <ExcerptCard
              key={`${excerpt.citation}-${index}`}
              excerpt={excerpt}
              onClick={() => onExcerptClick(excerpt)}
            />
          ))
        )}
      </div>
    </div>
  );
};

export default LegislationMapPanel;
