import { useCallback } from 'react';
import { StepData, GraphData, RulesResponse, DecisionTreeNode, LegislationMap, LegislativeExcerpt } from '../types';
import { useLexGraphStore, initialStepData, LexGraphEvaluation } from '../stores/lexGraphStore';

export interface UseLexGraphStreamReturn {
  // Input state (from store)
  scenario: string;
  setScenario: (scenario: string) => void;
  evalDate: string;
  setEvalDate: (date: string) => void;
  activeTab: 'rules' | 'graph';
  setActiveTab: (tab: 'rules' | 'graph') => void;

  // Processing state
  stepData: StepData;
  graphData: GraphData;
  loading: boolean;
  result: RulesResponse | null;
  error: string | null;

  // Legislative source integration state
  decisionTree: DecisionTreeNode | null;
  legislationMap: LegislationMap | null;
  selectedExcerpt: LegislativeExcerpt | null;
  viewMode: 'trace' | 'tree';
  setViewMode: (mode: 'trace' | 'tree') => void;
  setSelectedExcerpt: (excerpt: LegislativeExcerpt | null) => void;

  // History
  evaluationHistory: LexGraphEvaluation[];

  // Actions
  evaluate: (scenario: string, language: string, evalDate: string) => Promise<void>;
  reset: () => void;
  clearHistory: () => void;
}

export const useLexGraphStream = (): UseLexGraphStreamReturn => {
  // Get state and actions from store
  const {
    scenario,
    setScenario,
    evalDate,
    setEvalDate,
    activeTab,
    setActiveTab,
    stepData,
    graphData,
    loading,
    result,
    error,
    evaluationHistory,
    clearHistory,
    reset,
    performEvaluate,
    // Legislative source integration
    decisionTree,
    legislationMap,
    selectedExcerpt,
    viewMode,
    setViewMode,
    setSelectedExcerpt,
  } = useLexGraphStore();

  // No cleanup needed - streaming continues in background via store

  const evaluate = useCallback(
    async (scenarioText: string, language: string, evalDateStr: string) => {
      // Delegate to store action - runs in background independent of component lifecycle
      performEvaluate(scenarioText, language, evalDateStr);
    },
    [performEvaluate]
  );

  return {
    scenario,
    setScenario,
    evalDate,
    setEvalDate,
    activeTab,
    setActiveTab,
    stepData,
    graphData,
    loading,
    result,
    error,
    evaluationHistory,
    evaluate,
    reset,
    clearHistory,
    // Legislative source integration
    decisionTree,
    legislationMap,
    selectedExcerpt,
    viewMode,
    setViewMode,
    setSelectedExcerpt,
  };
};
