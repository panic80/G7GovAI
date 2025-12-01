import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import {
  StepData,
  StepStatus,
  GraphData,
  GraphNode,
  GraphLink,
  RulesResponse,
  LexGraphStreamEvent,
  LexGraphNodeName,
  ExtractedRule,
  TraceStep,
  DecisionResult,
  DecisionTreeNode,
  LegislationMap,
  LegislativeExcerpt,
  EnhancedRulesResponse,
} from '../types';
import { streamLexGraphEvaluation } from '../services/geminiService';
import { HISTORY_LIMITS, createCancelHandler, createHistoryItem } from './utils/streamingHelpers';
import { debugLog, debugWarn, debugError } from '../utils/debugLogger';

const NODE_ORDER: LexGraphNodeName[] = [
  'retrieve',
  'extract_rules',
  'resolve_thresholds',
  'map_legislation',
  'extract_facts',
  'evaluate',
];

function buildGraphFromRules(rules: ExtractedRule[]): GraphData {
  const nodes: GraphNode[] = [];
  const links: GraphLink[] = [];
  const nodeMap = new Map<string, boolean>();

  rules.forEach((rule) => {
    // Create node for rule
    if (!nodeMap.has(rule.rule_id)) {
      nodes.push({
        id: rule.rule_id,
        label: rule.description?.slice(0, 40) || rule.rule_id,
        group: 1, // Blue for rules
      });
      nodeMap.set(rule.rule_id, true);
    }

    // Create nodes for conditions
    (rule.conditions || []).forEach((cond) => {
      const condId = `${rule.rule_id}-${cond.fact_key}`;
      if (!nodeMap.has(condId)) {
        nodes.push({
          id: condId,
          label: `${cond.fact_key} ${cond.operator} ${cond.value}`,
          group: 2, // Red for conditions
        });
        nodeMap.set(condId, true);
      }
      links.push({ source: rule.rule_id, target: condId });
    });
  });

  return { nodes, links };
}

// Initial step data
const initialStepData: StepData = {
  retrieve: { status: 'pending', documents: [] },
  extract_rules: { status: 'pending', rules: [] },
  resolve_thresholds: { status: 'pending', resolvedRules: [], confidenceCounts: { high: 0, medium: 0, low: 0 } },
  map_legislation: { status: 'pending', legislationMap: null },
  extract_facts: { status: 'pending', facts: {} },
  evaluate: { status: 'pending', decision: null, trace: [], decisionTree: null },
};

// Evaluation history item for accumulated history
export interface LexGraphEvaluation {
  id: string;
  timestamp: string;
  scenario: string;
  evalDate: string;
  result: RulesResponse | null;
}

interface LexGraphState {
  // Input state (moved from component)
  scenario: string;
  evalDate: string;
  activeTab: 'rules' | 'graph';

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

  // Accumulated history
  evaluationHistory: LexGraphEvaluation[];

  // AbortController for background requests (not persisted)
  abortController: AbortController | null;
}

interface LexGraphActions {
  setScenario: (scenario: string) => void;
  setEvalDate: (evalDate: string) => void;
  setActiveTab: (tab: 'rules' | 'graph') => void;
  setStepData: (stepData: StepData) => void;
  updateStepData: (updater: (prev: StepData) => StepData) => void;
  setGraphData: (graphData: GraphData) => void;
  setLoading: (loading: boolean) => void;
  setResult: (result: RulesResponse | null) => void;
  setError: (error: string | null) => void;
  addEvaluationToHistory: (evaluation: Omit<LexGraphEvaluation, 'id' | 'timestamp'>) => void;
  clearHistory: () => void;
  reset: () => void;

  // Legislative source integration actions
  setDecisionTree: (tree: DecisionTreeNode | null) => void;
  setLegislationMap: (map: LegislationMap | null) => void;
  setSelectedExcerpt: (excerpt: LegislativeExcerpt | null) => void;
  setViewMode: (mode: 'trace' | 'tree') => void;

  // Background-safe evaluation actions
  performEvaluate: (scenario: string, language: string, evalDate: string) => Promise<void>;
  cancelEvaluation: () => void;
}

const initialState: LexGraphState = {
  scenario: '',
  evalDate: new Date().toISOString().split('T')[0],
  activeTab: 'rules',
  stepData: initialStepData,
  graphData: { nodes: [], links: [] },
  loading: false,
  result: null,
  error: null,
  // Legislative source integration
  decisionTree: null,
  legislationMap: null,
  selectedExcerpt: null,
  viewMode: 'trace',
  evaluationHistory: [],
  abortController: null,
};

export const useLexGraphStore = create<LexGraphState & LexGraphActions>()(
  persist(
    (set, get) => ({
      ...initialState,

      setScenario: (scenario) => set({ scenario }),
      setEvalDate: (evalDate) => set({ evalDate }),
      setActiveTab: (activeTab) => set({ activeTab }),
      setStepData: (stepData) => set({ stepData }),

      updateStepData: (updater) =>
        set((state) => ({ stepData: updater(state.stepData) })),

      setGraphData: (graphData) => set({ graphData }),
      setLoading: (loading) => set({ loading }),
      setResult: (result) => set({ result }),
      setError: (error) => set({ error }),

      addEvaluationToHistory: (evaluation) =>
        set((state) => ({
          evaluationHistory: [
            ...state.evaluationHistory,
            createHistoryItem(evaluation),
          ].slice(-HISTORY_LIMITS.EVALUATIONS),
        })),

      clearHistory: () => set({ evaluationHistory: [] }),

      reset: () =>
        set({
          stepData: initialStepData,
          graphData: { nodes: [], links: [] },
          result: null,
          error: null,
          loading: false,
          decisionTree: null,
          legislationMap: null,
          selectedExcerpt: null,
        }),

      // Legislative source integration actions
      setDecisionTree: (tree) => set({ decisionTree: tree }),
      setLegislationMap: (map) => set({ legislationMap: map }),
      setSelectedExcerpt: (excerpt) => set({ selectedExcerpt: excerpt }),
      setViewMode: (mode) => set({ viewMode: mode }),

      cancelEvaluation: createCancelHandler(get, set),

      performEvaluate: async (scenarioText: string, language: string, evalDateStr: string) => {
        // Abort any existing request
        get().abortController?.abort();
        const controller = new AbortController();

        // Reset state and start loading
        set({
          abortController: controller,
          stepData: initialStepData,
          graphData: { nodes: [], links: [] },
          result: null,
          error: null,
          loading: true,
          decisionTree: null,
          legislationMap: null,
          selectedExcerpt: null,
        });

        // Mark first step as in_progress
        set((state) => ({
          stepData: {
            ...state.stepData,
            retrieve: { ...state.stepData.retrieve, status: 'in_progress' as StepStatus },
          },
        }));

        try {
          await streamLexGraphEvaluation(
            scenarioText,
            language,
            evalDateStr,
            (event: LexGraphStreamEvent) => {
              if (controller.signal.aborted) return;

              const { node, state: eventState } = event;
              debugLog(`[LexGraph] Node completed: ${node}`, eventState);

              // Update the completed node's data
              set((currentState) => {
                const updated = { ...currentState.stepData };

                // Mark current node as completed with its data
                if (node === 'retrieve') {
                  updated.retrieve = {
                    status: 'completed',
                    documents: eventState.documents || [],
                  };
                } else if (node === 'extract_rules') {
                  let rules: ExtractedRule[] = [];
                  if (eventState.extracted_rules) {
                    try {
                      rules = JSON.parse(eventState.extracted_rules);
                    } catch (e) {
                      debugWarn('Failed to parse extracted_rules', e);
                    }
                  }
                  updated.extract_rules = { status: 'completed', rules };
                } else if (node === 'resolve_thresholds') {
                  let resolvedRules: ExtractedRule[] = [];
                  if (eventState.resolved_rules) {
                    try {
                      resolvedRules = JSON.parse(eventState.resolved_rules);
                    } catch (e) {
                      debugWarn('Failed to parse resolved_rules', e);
                    }
                  }
                  // Count confidence levels
                  let high = 0, medium = 0, low = 0;
                  resolvedRules.forEach((r) => {
                    (r.conditions || []).forEach((c) => {
                      if (c.confidence === 'HIGH') high++;
                      else if (c.confidence === 'MEDIUM') medium++;
                      else if (c.confidence === 'LOW') low++;
                    });
                  });
                  updated.resolve_thresholds = {
                    status: 'completed',
                    resolvedRules,
                    confidenceCounts: { high, medium, low },
                  };
                  // Build graph from resolved rules
                  set({ graphData: buildGraphFromRules(resolvedRules) });
                } else if (node === 'map_legislation') {
                  // Handle legislation map from state
                  const legMap = eventState.legislation_map || { primary: [], related: [], definitions: [] };
                  updated.map_legislation = {
                    status: 'completed',
                    legislationMap: legMap,
                  };
                  // Store in root state for components to access
                  set({ legislationMap: legMap });
                } else if (node === 'extract_facts') {
                  let facts: Record<string, unknown> = {};
                  const factsJson = eventState.generated_queries?.[eventState.generated_queries.length - 1];
                  if (factsJson) {
                    try {
                      const parsed = JSON.parse(factsJson);
                      facts = parsed.facts || parsed;
                    } catch (e) {
                      debugWarn('Failed to parse facts', e);
                    }
                  }
                  updated.extract_facts = { status: 'completed', facts };
                } else if (node === 'evaluate') {
                  let decision: DecisionResult | null = null;
                  let trace: TraceStep[] = [];
                  let decisionTreeData: DecisionTreeNode | null = null;
                  if (eventState.final_answer) {
                    try {
                      const finalAnswer: EnhancedRulesResponse = JSON.parse(eventState.final_answer);
                      decision = finalAnswer.decision;
                      trace = finalAnswer.trace || [];
                      decisionTreeData = finalAnswer.decision_tree || eventState.decision_tree || null;
                      set({
                        result: finalAnswer,
                        decisionTree: decisionTreeData,
                        // Also update legislation map if present in final answer
                        ...(finalAnswer.legislation_map && { legislationMap: finalAnswer.legislation_map }),
                      });

                      // Add to evaluation history
                      get().addEvaluationToHistory({
                        scenario: scenarioText,
                        evalDate: evalDateStr,
                        result: finalAnswer,
                      });
                    } catch (e) {
                      debugWarn('Failed to parse final_answer', e);
                    }
                  }
                  updated.evaluate = { status: 'completed', decision, trace, decisionTree: decisionTreeData };
                }

                // Mark next node as in_progress
                const nodeIdx = NODE_ORDER.indexOf(node);
                if (nodeIdx >= 0 && nodeIdx < NODE_ORDER.length - 1) {
                  const nextNode = NODE_ORDER[nodeIdx + 1];
                  (updated as any)[nextNode] = {
                    ...(updated as any)[nextNode],
                    status: 'in_progress' as StepStatus,
                  };
                }

                return { stepData: updated };
              });
            },
            controller.signal
          );
        } catch (e) {
          if (controller.signal.aborted) return;
          debugError('LexGraph evaluation error:', e);
          set({ error: String(e) });

          // Mark current in_progress step as error
          set((state) => {
            const updated = { ...state.stepData };
            for (const key of NODE_ORDER) {
              if ((updated as any)[key].status === 'in_progress') {
                (updated as any)[key] = { ...(updated as any)[key], status: 'error' as StepStatus };
                break;
              }
            }
            return { stepData: updated };
          });
        } finally {
          if (!controller.signal.aborted) {
            set({ loading: false });
          }
        }
      },
    }),
    {
      name: 'lexgraph-session',
      storage: createJSONStorage(() => sessionStorage),
      // Only persist these fields
      partialize: (state) => ({
        scenario: state.scenario,
        evalDate: state.evalDate,
        activeTab: state.activeTab,
        result: state.result,
        graphData: state.graphData,
        evaluationHistory: state.evaluationHistory,
      }),
    }
  )
);

// Export initial step data for use in hook
export { initialStepData };
