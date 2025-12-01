import React, { useEffect, useRef, useState } from 'react';
import { Search, User, Bot, BrainCircuit, Database, Filter, X, ChevronDown, ChevronUp } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useLanguage } from '../contexts/LanguageContext';
import { GovLensResults } from './GovLensResults';
import { GovLensProgressPanel } from './GovLensProgressPanel';
import { useGovLensSearch } from '../hooks/useGovLensSearch';

export const GovLens: React.FC = () => {
  const {
    query, setQuery, loading, currentQuery, results, streamingTrace = [],
    handleSearch, clearResults, mode, setMode,
    selectedFilters, availableFilters, filtersLoading, hasActiveFilters, updateFilters, clearFilters
  } = useGovLensSearch();
  const { t } = useLanguage();
  const chatEndRef = useRef<HTMLDivElement>(null);
  const [filterPanelOpen, setFilterPanelOpen] = useState(false);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [results, loading, streamingTrace]);

  return (
    <div className="max-w-5xl mx-auto p-6 flex flex-col h-[calc(100vh-100px)]">
      <header className="flex-none mb-4 flex justify-between items-center">
        <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Search className="w-6 h-6 text-gov-blue" />
            {t('nav.govlens')}
            </h1>
            <p className="text-sm text-gray-500">{t('govlens.subtitle')}</p>
        </div>
        <div className="flex gap-4 items-center">
            <Link
                to="/knowledge-base"
                className="flex items-center gap-2 text-sm text-gov-blue hover:underline"
            >
                <Database size={16} />
                {t('nav.knowledgebase')}
            </Link>
            {results.length > 0 && (
                <button onClick={clearResults} className="text-sm text-red-500 hover:underline">
                    {t('govlens.clearChat')}
                </button>
            )}
        </div>
      </header>

      {/* Chat Area - Flexible Growth */}
      <div className="flex-grow overflow-y-auto space-y-6 pr-4 pb-4 scroll-smooth">

        {/* Empty State */}
        {results.length === 0 && !loading && (
            <div className="flex flex-col items-center justify-center h-full text-gray-400 gap-4">
                <Bot size={48} className="opacity-20" />
                <p>{t('govlens.emptyState')}</p>
            </div>
        )}

        {/* Render Q&A Pairs from results array */}
        {results.map((qa, idx) => (
          <div key={idx} className="space-y-4">
            {/* User Question */}
            <div className="flex gap-4 justify-end">
              <div className="p-4 rounded-2xl max-w-[80%] shadow-sm text-sm leading-relaxed bg-blue-600 text-white rounded-br-none">
                {qa.query}
              </div>
              <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center flex-shrink-0">
                <User className="text-gray-500 w-5 h-5" />
              </div>
            </div>

            {/* Result (rich panel for RAG, semantic results for semantic) */}
            <div className="animate-fade-in">
              <GovLensResults result={qa.result} />
            </div>
          </div>
        ))}

        {/* Loading Indicator with current query */}
        {loading && currentQuery && (
          <div className="space-y-4">
            {/* Show the current query */}
            <div className="flex gap-4 justify-end">
              <div className="p-4 rounded-2xl max-w-[80%] shadow-sm text-sm leading-relaxed bg-blue-600 text-white rounded-br-none">
                {currentQuery}
              </div>
              <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center flex-shrink-0">
                <User className="text-gray-500 w-5 h-5" />
              </div>
            </div>

            {/* Progress panel */}
            <div className="flex gap-4 justify-start animate-fade-in">
              <div className="w-8 h-8 rounded-full bg-gov-blue flex items-center justify-center flex-shrink-0">
                <Bot className="text-white w-5 h-5" />
              </div>
              <GovLensProgressPanel streamingTrace={streamingTrace} />
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* Search Mode Toggle + Filters */}
      <div className="flex justify-center items-center gap-3 mb-3">
        <div className="relative bg-gray-100 p-1.5 rounded-xl inline-flex items-center shadow-inner">
          {/* Sliding indicator */}
          <div
            className={`absolute top-1.5 bottom-1.5 w-[calc(50%-6px)] bg-gov-blue rounded-lg transition-all duration-300 ease-out shadow-md ${
              mode === 'rag' ? 'left-1.5' : 'left-[calc(50%+3px)]'
            }`}
          />

          <button
            type="button"
            onClick={() => setMode('rag')}
            className={`relative z-10 flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-colors duration-200 ${
              mode === 'rag' ? 'text-white' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <BrainCircuit size={18} />
            {t('govlens.mode.rag')}
          </button>

          <button
            type="button"
            onClick={() => setMode('semantic')}
            className={`relative z-10 flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-colors duration-200 ${
              mode === 'semantic' ? 'text-white' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <Search size={18} />
            {t('govlens.mode.semantic')}
          </button>
        </div>

        {/* Filter Toggle Button */}
        <button
          type="button"
          onClick={() => setFilterPanelOpen(!filterPanelOpen)}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all border ${
            hasActiveFilters
              ? 'bg-gov-blue text-white border-gov-blue'
              : 'bg-white text-gray-600 border-gray-300 hover:border-gov-blue hover:text-gov-blue'
          }`}
        >
          <Filter size={14} />
          {t('govlens.filters.label')}
          {hasActiveFilters && (
            <span className="bg-white text-gov-blue px-1.5 py-0.5 rounded-full text-[10px] font-bold">
              {selectedFilters.categories.length}
            </span>
          )}
          {filterPanelOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>
      </div>

      {/* Collapsible Filter Panel */}
      {filterPanelOpen && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-3 animate-fade-in">
          <div className="flex justify-between items-start mb-3">
            <h3 className="text-sm font-medium text-gray-700">{t('govlens.filters.title')}</h3>
            {hasActiveFilters && (
              <button
                type="button"
                onClick={clearFilters}
                className="text-xs text-red-500 hover:text-red-700 flex items-center gap-1"
              >
                <X size={12} />
                {t('govlens.filters.clearAll')}
              </button>
            )}
          </div>

          {filtersLoading ? (
            <div className="text-sm text-gray-400 italic">{t('govlens.filters.loading')}</div>
          ) : (
            <div className="space-y-4">
              {/* Categories */}
              <div>
                <label className="text-xs font-medium text-gray-500 mb-2 block">{t('govlens.filters.categories')}</label>
                <div className="flex flex-wrap gap-2">
                  {availableFilters.categories.map(cat => (
                    <button
                      key={cat}
                      type="button"
                      onClick={() => {
                        const isSelected = selectedFilters.categories.includes(cat);
                        updateFilters({
                          categories: isSelected
                            ? selectedFilters.categories.filter(c => c !== cat)
                            : [...selectedFilters.categories, cat]
                        });
                      }}
                      className={`px-3 py-1 rounded-full text-xs font-medium transition-all ${
                        selectedFilters.categories.includes(cat)
                          ? 'bg-gov-blue text-white'
                          : 'bg-white border border-gray-300 text-gray-600 hover:border-gov-blue hover:text-gov-blue'
                      }`}
                    >
                      {cat}
                    </button>
                  ))}
                  {availableFilters.categories.length === 0 && (
                    <span className="text-xs text-gray-400 italic">{t('govlens.filters.noCategories')}</span>
                  )}
                </div>
              </div>

            </div>
          )}
        </div>
      )}

      {/* Input Area - Fixed Bottom */}
      <form onSubmit={handleSearch} className="relative flex-none">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t('govlens.placeholder')}
          disabled={loading}
          className="w-full p-4 pl-6 pr-32 rounded-full border border-gray-300 shadow-sm focus:ring-2 focus:ring-gov-blue focus:border-gov-blue outline-none transition disabled:bg-gray-50"
        />
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="absolute right-2 top-2 bottom-2 bg-gov-blue text-white px-6 rounded-full hover:bg-blue-800 transition disabled:opacity-50 flex items-center gap-2 font-medium"
        >
          {loading ? t('govlens.sending') : t('btn.search')}
          {!loading && <Search className="w-4 h-4" />}
        </button>
      </form>
    </div>
  );
};
