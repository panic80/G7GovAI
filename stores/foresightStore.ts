import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { StepStatus } from '../types';
import { CapitalPlanResponse, EmergencySimResponse } from '../services/foresightService';
import { streamWithCallback } from '../services/apiClient';
import { HISTORY_LIMITS, createHistoryItem } from './utils/streamingHelpers';
import { debugError } from '../utils/debugLogger';

// Step data types
export interface ForesightStepData {
  parse_request: { status: StepStatus; query?: string };
  retrieve_assets: { status: StepStatus; assets: any[]; assetCount: number };
  calculate_risks: { status: StepStatus; riskScores: any[]; riskDistribution: Record<string, number> };
  optimize_allocation: { status: StepStatus; allocations: any[]; totalAllocated: number; assetsFunded: number };
  synthesize: { status: StepStatus; recommendations: string; confidence: number };
}

export interface ForesightResult {
  allocations: any[];
  totalRequested: number;
  totalAllocated: number;
  assetsFunded: number;
  assetsDeferred: number;
  riskReductionPct: number;
  recommendations: string;
  confidence: number;
}

export interface ForesightOptimizeParams {
  budgetTotal: number;
  weights: { risk: number; coverage: number };
  language: string;
}

// Initial step data
const initialStepData: ForesightStepData = {
  parse_request: { status: 'pending', query: undefined },
  retrieve_assets: { status: 'pending', assets: [], assetCount: 0 },
  calculate_risks: { status: 'pending', riskScores: [], riskDistribution: {} },
  optimize_allocation: { status: 'pending', allocations: [], totalAllocated: 0, assetsFunded: 0 },
  synthesize: { status: 'pending', recommendations: '', confidence: 0 },
};

// Tab type
export type ForesightTab = 'agent' | 'capital' | 'emergency' | 'forecast';

// Planning history item
export interface ForesightPlanningSession {
  id: string;
  timestamp: string;
  type: ForesightTab;
  params: Record<string, unknown>;
  result: ForesightResult | CapitalPlanResponse | EmergencySimResponse | null;
}

interface ForesightState {
  // UI state
  activeTab: ForesightTab;

  // Agent tab state
  agentBudget: number;
  agentRiskWeight: number;
  agentStepData: ForesightStepData;
  agentTraceLog: string[];
  agentLoading: boolean;
  agentResult: ForesightResult | null;
  agentError: string | null;

  // Capital planning tab state
  capitalBudget: number;
  capitalRiskWeight: number;
  capitalImpactWeight: number;
  capitalPlan: CapitalPlanResponse | null;
  capitalLoading: boolean;

  // Emergency sim tab state
  emergencyEventType: string;
  emergencySim: EmergencySimResponse | null;
  emergencyLoading: boolean;

  // Forecast tab state
  forecastHorizonYears: number;
  forecastLoading: boolean;
  conditionForecasts: any[];
  demandForecasts: any[];
  riskTimeline: any | null;
  externalFactors: any | null;
  bottlenecks: any[];

  // Accumulated history
  planningHistory: ForesightPlanningSession[];

  // AbortController for background requests (not persisted)
  abortController: AbortController | null;
}

interface ForesightActions {
  // UI actions
  setActiveTab: (tab: ForesightTab) => void;

  // Agent tab actions
  setAgentBudget: (budget: number) => void;
  setAgentRiskWeight: (weight: number) => void;
  setAgentStepData: (stepDataOrUpdater: ForesightStepData | ((prev: ForesightStepData) => ForesightStepData)) => void;
  setAgentTraceLog: (trace: string[]) => void;
  appendAgentTraceLog: (logs: string[]) => void;
  setAgentLoading: (loading: boolean) => void;
  setAgentResult: (result: ForesightResult | null) => void;
  updateAgentResult: (updater: (prev: ForesightResult | null) => ForesightResult | null) => void;
  setAgentError: (error: string | null) => void;
  resetAgent: () => void;

  // Capital planning actions
  setCapitalBudget: (budget: number) => void;
  setCapitalRiskWeight: (weight: number) => void;
  setCapitalImpactWeight: (weight: number) => void;
  setCapitalPlan: (plan: CapitalPlanResponse | null) => void;
  setCapitalLoading: (loading: boolean) => void;
  updateCapitalWeights: (riskWeight: number) => void;

  // Emergency sim actions
  setEmergencyEventType: (eventType: string) => void;
  setEmergencySim: (sim: EmergencySimResponse | null) => void;
  setEmergencyLoading: (loading: boolean) => void;

  // Forecast actions
  setForecastHorizonYears: (years: number) => void;
  setForecastLoading: (loading: boolean) => void;
  setConditionForecasts: (forecasts: any[]) => void;
  setDemandForecasts: (forecasts: any[]) => void;
  setRiskTimeline: (timeline: any | null) => void;
  setExternalFactors: (factors: any | null) => void;
  setBottlenecks: (bottlenecks: any[]) => void;
  resetForecast: () => void;

  // History actions
  addPlanningToHistory: (session: Omit<ForesightPlanningSession, 'id' | 'timestamp'>) => void;
  clearHistory: () => void;

  // Background-safe agent optimization actions
  performOptimize: (params: ForesightOptimizeParams) => Promise<void>;
  cancelOptimize: () => void;
}

const initialState: ForesightState = {
  activeTab: 'agent',

  // Agent tab
  agentBudget: 10000000,
  agentRiskWeight: 0.5,
  agentStepData: initialStepData,
  agentTraceLog: [],
  agentLoading: false,
  agentResult: null,
  agentError: null,

  // Capital planning
  capitalBudget: 50000000,
  capitalRiskWeight: 0.5,
  capitalImpactWeight: 0.5,
  capitalPlan: null,
  capitalLoading: false,

  // Emergency sim
  emergencyEventType: 'None',
  emergencySim: null,
  emergencyLoading: false,

  // Forecast
  forecastHorizonYears: 5,
  forecastLoading: false,
  conditionForecasts: [],
  demandForecasts: [],
  riskTimeline: null,
  externalFactors: null,
  bottlenecks: [],

  // History
  planningHistory: [],

  // AbortController
  abortController: null,
};

export const useForesightStore = create<ForesightState & ForesightActions>()(
  persist(
    (set, get) => ({
      ...initialState,

      // UI actions
      setActiveTab: (activeTab) => set({ activeTab }),

      // Agent tab actions
      setAgentBudget: (agentBudget) => set({ agentBudget }),
      setAgentRiskWeight: (agentRiskWeight) => set({ agentRiskWeight }),
      setAgentStepData: (stepDataOrUpdater) =>
        set((state) => ({
          agentStepData: typeof stepDataOrUpdater === 'function'
            ? stepDataOrUpdater(state.agentStepData)
            : stepDataOrUpdater,
        })),
      setAgentTraceLog: (agentTraceLog) => set({ agentTraceLog }),
      appendAgentTraceLog: (logs) =>
        set((state) => ({ agentTraceLog: [...state.agentTraceLog, ...logs] })),
      setAgentLoading: (agentLoading) => set({ agentLoading }),
      setAgentResult: (agentResult) => set({ agentResult }),
      updateAgentResult: (updater) =>
        set((state) => ({ agentResult: updater(state.agentResult) })),
      setAgentError: (agentError) => set({ agentError }),
      resetAgent: () =>
        set({
          agentStepData: initialStepData,
          agentTraceLog: [],
          agentResult: null,
          agentError: null,
          agentLoading: false,
        }),

      // Capital planning actions
      setCapitalBudget: (capitalBudget) => set({ capitalBudget }),
      setCapitalRiskWeight: (capitalRiskWeight) => set({ capitalRiskWeight }),
      setCapitalImpactWeight: (capitalImpactWeight) => set({ capitalImpactWeight }),
      setCapitalPlan: (capitalPlan) => set({ capitalPlan }),
      setCapitalLoading: (capitalLoading) => set({ capitalLoading }),
      updateCapitalWeights: (riskWeight) =>
        set({
          capitalRiskWeight: riskWeight,
          capitalImpactWeight: parseFloat((1 - riskWeight).toFixed(1)),
        }),

      // Emergency sim actions
      setEmergencyEventType: (emergencyEventType) => set({ emergencyEventType }),
      setEmergencySim: (emergencySim) => set({ emergencySim }),
      setEmergencyLoading: (emergencyLoading) => set({ emergencyLoading }),

      // Forecast actions
      setForecastHorizonYears: (forecastHorizonYears) => set({ forecastHorizonYears }),
      setForecastLoading: (forecastLoading) => set({ forecastLoading }),
      setConditionForecasts: (conditionForecasts) => set({ conditionForecasts }),
      setDemandForecasts: (demandForecasts) => set({ demandForecasts }),
      setRiskTimeline: (riskTimeline) => set({ riskTimeline }),
      setExternalFactors: (externalFactors) => set({ externalFactors }),
      setBottlenecks: (bottlenecks) => set({ bottlenecks }),
      resetForecast: () => set({
        conditionForecasts: [],
        demandForecasts: [],
        riskTimeline: null,
        externalFactors: null,
        bottlenecks: [],
        forecastLoading: false,
      }),

      // History actions
      addPlanningToHistory: (session) =>
        set((state) => ({
          planningHistory: [
            ...state.planningHistory,
            createHistoryItem(session),
          ].slice(-HISTORY_LIMITS.PLANNING_SESSIONS),
        })),

      clearHistory: () => set({ planningHistory: [] }),

      cancelOptimize: () => {
        const controller = get().abortController;
        if (controller) {
          controller.abort();
          set({ abortController: null, agentLoading: false });
        }
      },

      performOptimize: async (params: ForesightOptimizeParams) => {
        // Abort any existing request
        get().abortController?.abort();
        const controller = new AbortController();

        // Reset state
        set({
          abortController: controller,
          agentStepData: initialStepData,
          agentTraceLog: [],
          agentResult: null,
          agentError: null,
          agentLoading: true,
        });

        // Track current result for history
        let currentResult: ForesightResult | null = null;

        // Define event handler for stream events
        const handleEvent = (event: { node: string; state: Record<string, any> }) => {
          if (controller.signal.aborted) return;

          const nodeName = event.node;
          const eventState = event.state || {};

          // Handle error node
          if (nodeName === 'error') {
            set({ agentError: eventState.error || 'Unknown error' });
            return;
          }

          // Handle complete node
          if (nodeName === 'complete') {
            return;
          }

          // Update trace log
          if (eventState.trace_log && Array.isArray(eventState.trace_log)) {
            set((s) => ({ agentTraceLog: [...s.agentTraceLog, ...eventState.trace_log] }));
          }

          // Update step data based on node
          if (nodeName === 'route') {
            set({
              agentStepData: {
                ...initialStepData,
                parse_request: { status: 'completed', query: eventState.optimization_path },
              },
            });
          } else if (nodeName === 'retrieve') {
            const assets = eventState.retrieved_assets || [];
            set((s) => ({
              agentStepData: {
                ...s.agentStepData,
                retrieve_assets: { status: 'completed', assets, assetCount: assets.length },
              },
            }));
          } else if (nodeName === 'analyze') {
            const recommendations = eventState.recommendations || [];
            const analysis = eventState.analysis_result || {};

            set((s) => ({
              agentStepData: {
                ...s.agentStepData,
                calculate_risks: {
                  status: 'completed',
                  riskScores: eventState.risk_scores || [],
                  riskDistribution: { high: 0, critical: 0 },
                },
                optimize_allocation: {
                  status: 'completed',
                  allocations: recommendations,
                  totalAllocated: analysis.total_allocated || 0,
                  assetsFunded: analysis.assets_funded || 0,
                },
              },
            }));

            // Build result
            const newResult: ForesightResult = {
              allocations: recommendations,
              totalRequested: analysis.total_requested || params.budgetTotal,
              totalAllocated: analysis.total_allocated || 0,
              assetsFunded: analysis.assets_funded || 0,
              assetsDeferred: analysis.assets_deferred || 0,
              riskReductionPct: analysis.risk_reduction_pct || 0,
              recommendations: analysis.summary || '',
              confidence: eventState.overall_confidence || 0.8,
            };
            currentResult = newResult;
            set({ agentResult: newResult });
          } else if (nodeName === 'synthesize') {
            const analysis = eventState.analysis_result || {};
            const confidence = eventState.overall_confidence || 0.8;
            const summary = analysis.summary || '';

            set((s) => ({
              agentStepData: {
                ...s.agentStepData,
                synthesize: {
                  status: 'completed',
                  recommendations: summary,
                  confidence: confidence,
                },
              },
            }));

            // Update final result with summary
            set((s) => {
              const prev = s.agentResult;
              if (!prev) {
                currentResult = {
                  allocations: [],
                  totalRequested: params.budgetTotal,
                  totalAllocated: 0,
                  assetsFunded: 0,
                  assetsDeferred: 0,
                  riskReductionPct: 0,
                  recommendations: summary,
                  confidence: confidence,
                };
              } else {
                currentResult = {
                  ...prev,
                  recommendations: summary || prev.recommendations,
                  confidence: confidence,
                };
              }
              return { agentResult: currentResult };
            });

            // Add to history
            get().addPlanningToHistory({
              type: 'agent',
              params: {
                budget: params.budgetTotal,
                weights: params.weights,
              },
              result: currentResult,
            });
          }
        };

        try {
          await streamWithCallback<{ node: string; state: Record<string, any> }>(
            '/agent/foresight/stream',
            {
              query: `Optimize capital allocation for $${params.budgetTotal.toLocaleString()} budget`,
              language: params.language,
              budget_total: params.budgetTotal,
              planning_horizon_years: 5,
              weights: params.weights,
              include_scenarios: true,
            },
            handleEvent,
            controller.signal
          );
        } catch (err) {
          if (controller.signal.aborted) return;
          set({ agentError: (err as Error).message });
        } finally {
          if (!controller.signal.aborted) {
            set({ agentLoading: false });
          }
        }
      },
    }),
    {
      name: 'foresight-session',
      storage: createJSONStorage(() => sessionStorage),
      // Only persist these fields
      partialize: (state) => ({
        activeTab: state.activeTab,
        agentBudget: state.agentBudget,
        agentRiskWeight: state.agentRiskWeight,
        agentResult: state.agentResult,
        capitalBudget: state.capitalBudget,
        capitalRiskWeight: state.capitalRiskWeight,
        capitalImpactWeight: state.capitalImpactWeight,
        capitalPlan: state.capitalPlan,
        emergencyEventType: state.emergencyEventType,
        emergencySim: state.emergencySim,
        planningHistory: state.planningHistory,
      }),
    }
  )
);

// Export initial step data for use in hooks
export { initialStepData };
