import React from 'react';
import { GitMerge, FileText, Network } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';
import { RuleEvaluator } from './LexGraph/RuleEvaluator';
import { GraphVisualizer } from './LexGraph/GraphVisualizer';
import { useLexGraphStream } from '../hooks/useLexGraphStream';

export const LexGraph: React.FC = () => {
  const { language, t } = useLanguage();

  // All state now comes from the hook (backed by Zustand store)
  const {
    activeTab,
    setActiveTab,
    scenario,
    setScenario,
    evalDate,
    setEvalDate,
    stepData,
    graphData,
    loading,
    result,
    error,
    evaluate,
    reset,
    // Legislative source integration
    decisionTree,
    legislationMap,
    viewMode,
    setViewMode,
  } = useLexGraphStream();

  const handleEvaluate = () => {
    if (!scenario.trim()) return;
    evaluate(scenario, language, evalDate);
  };

  return (
    <div className="max-w-7xl mx-auto p-6 h-[calc(100vh-100px)] flex flex-col">
      <header className="mb-6 flex justify-between items-end">
        <div>
            <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
            <GitMerge className="w-8 h-8 text-gov-blue" />
            {t('nav.lexgraph')} <span className="text-lg font-normal text-gray-500">| {t('nav.lexgraph.desc')}</span>
            </h1>
            <p className="text-gray-600 mt-2">
              {t('lexgraph.subtitle')}
            </p>
        </div>

        {/* Tabs */}
        <div className="flex space-x-1 bg-gray-100 p-1 rounded-lg">
            <button
                onClick={() => setActiveTab('rules')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors flex items-center gap-2 ${
                    activeTab === 'rules' ? 'bg-white text-gov-blue shadow-sm' : 'text-gray-500 hover:text-gray-700'
                }`}
            >
                <FileText size={16} />
                {t('lexgraph.tab.rules')}
            </button>
            <button
                onClick={() => setActiveTab('graph')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors flex items-center gap-2 ${
                    activeTab === 'graph' ? 'bg-white text-gov-blue shadow-sm' : 'text-gray-500 hover:text-gray-700'
                }`}
            >
                <Network size={16} />
                {t('lexgraph.tab.graph')}
            </button>
        </div>
      </header>

      {activeTab === 'rules' ? (
        <RuleEvaluator
          scenario={scenario}
          setScenario={setScenario}
          evalDate={evalDate}
          setEvalDate={setEvalDate}
          loading={loading}
          stepData={stepData}
          result={result}
          error={error}
          onEvaluate={handleEvaluate}
          onReset={reset}
          // Legislative source integration
          decisionTree={decisionTree}
          legislationMap={legislationMap}
          viewMode={viewMode}
          onViewModeChange={setViewMode}
        />
      ) : (
        <GraphVisualizer
          graphData={graphData}
          stepData={stepData}
          loading={loading}
        />
      )}
    </div>
  );
};
