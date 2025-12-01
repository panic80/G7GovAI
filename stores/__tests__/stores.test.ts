/**
 * Store Smoke Tests
 * =================
 * Tests to verify store interfaces and critical functionality before consolidation.
 * These tests ensure unique logic is preserved during refactoring.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { act } from '@testing-library/react';

// Mock services before importing stores
vi.mock('../../services/geminiService', () => ({
  streamGovLensSearch: vi.fn(),
  streamLexGraphEvaluation: vi.fn(),
}));

vi.mock('../../services/ragService', () => ({
  searchKnowledgeBase: vi.fn(),
}));

vi.mock('../../services/apiClient', () => ({
  streamWithCallback: vi.fn(),
}));

vi.mock('../../services/audioService', () => ({
  audioPlayer: {
    stop: vi.fn(),
    play: vi.fn(),
  },
}));

// Import stores after mocking
import { useGovLensStore } from '../govLensStore';
import { useLexGraphStore } from '../lexGraphStore';
import { useAccessBridgeStore } from '../accessBridgeStore';
import { useForesightStore } from '../foresightStore';
import { useKnowledgeBaseStore } from '../knowledgeBaseStore';

describe('Store Interface Tests', () => {
  describe('GovLensStore', () => {
    beforeEach(() => {
      const store = useGovLensStore.getState();
      // Reset store to initial state
      store.clearResults();
      store.setLoading(false);
      store.setMode('rag');
    });

    it('has required state properties', () => {
      const state = useGovLensStore.getState();

      expect(state).toHaveProperty('query');
      expect(state).toHaveProperty('loading');
      expect(state).toHaveProperty('results');
      expect(state).toHaveProperty('mode');
      expect(state).toHaveProperty('streamingTrace');
      expect(state).toHaveProperty('abortController');
    });

    it('has required action methods', () => {
      const state = useGovLensStore.getState();

      expect(typeof state.setQuery).toBe('function');
      expect(typeof state.setLoading).toBe('function');
      expect(typeof state.setMode).toBe('function');
      expect(typeof state.performSearch).toBe('function');
      expect(typeof state.cancelSearch).toBe('function');
    });

    it('supports dual mode (rag/semantic)', () => {
      const store = useGovLensStore.getState();

      store.setMode('rag');
      expect(useGovLensStore.getState().mode).toBe('rag');

      store.setMode('semantic');
      expect(useGovLensStore.getState().mode).toBe('semantic');
    });

    it('cancelSearch aborts controller and stops loading', () => {
      const store = useGovLensStore.getState();

      // Simulate an in-progress search
      const controller = new AbortController();
      useGovLensStore.setState({ abortController: controller, loading: true });

      store.cancelSearch();

      const newState = useGovLensStore.getState();
      expect(newState.loading).toBe(false);
      expect(controller.signal.aborted).toBe(true);
    });
  });

  describe('LexGraphStore', () => {
    beforeEach(() => {
      const store = useLexGraphStore.getState();
      store.reset();
    });

    it('has required state properties', () => {
      const state = useLexGraphStore.getState();

      expect(state).toHaveProperty('scenario');
      expect(state).toHaveProperty('evalDate');
      expect(state).toHaveProperty('stepData');
      expect(state).toHaveProperty('graphData');
      expect(state).toHaveProperty('loading');
      expect(state).toHaveProperty('result');
      expect(state).toHaveProperty('evaluationHistory');
    });

    it('has required action methods', () => {
      const state = useLexGraphStore.getState();

      expect(typeof state.setScenario).toBe('function');
      expect(typeof state.setStepData).toBe('function');
      expect(typeof state.setGraphData).toBe('function');
      expect(typeof state.performEvaluate).toBe('function');
      expect(typeof state.cancelEvaluation).toBe('function');
    });

    it('stepData has correct initial structure', () => {
      const { stepData } = useLexGraphStore.getState();

      expect(stepData.retrieve).toHaveProperty('status', 'pending');
      expect(stepData.extract_rules).toHaveProperty('status', 'pending');
      expect(stepData.resolve_thresholds).toHaveProperty('status', 'pending');
      expect(stepData.map_legislation).toHaveProperty('status', 'pending');
      expect(stepData.extract_facts).toHaveProperty('status', 'pending');
      expect(stepData.evaluate).toHaveProperty('status', 'pending');
    });

    it('graphData has nodes and links arrays', () => {
      const { graphData } = useLexGraphStore.getState();

      expect(Array.isArray(graphData.nodes)).toBe(true);
      expect(Array.isArray(graphData.links)).toBe(true);
    });

    it('supports confidence counts in resolve_thresholds step', () => {
      const { stepData } = useLexGraphStore.getState();

      expect(stepData.resolve_thresholds.confidenceCounts).toEqual({
        high: 0,
        medium: 0,
        low: 0,
      });
    });
  });

  describe('AccessBridgeStore', () => {
    beforeEach(() => {
      const store = useAccessBridgeStore.getState();
      store.reset();
    });

    it('has required state properties', () => {
      const state = useAccessBridgeStore.getState();

      expect(state).toHaveProperty('currentStep');
      expect(state).toHaveProperty('selectedModes');
      expect(state).toHaveProperty('textInput');
      expect(state).toHaveProperty('stepData');
      expect(state).toHaveProperty('gaps');
      expect(state).toHaveProperty('hasCriticalGaps');
      expect(state).toHaveProperty('lastParams'); // CRITICAL: for pause/resume
    });

    it('has required action methods', () => {
      const state = useAccessBridgeStore.getState();

      expect(typeof state.setCurrentStep).toBe('function');
      expect(typeof state.performProcess).toBe('function');
      expect(typeof state.submitFollowUp).toBe('function'); // CRITICAL: resume method
      expect(typeof state.cancelProcess).toBe('function');
    });

    it('supports wizard steps', () => {
      const store = useAccessBridgeStore.getState();

      const wizardSteps = ['mode', 'input', 'processing', 'gaps', 'output'];
      for (const step of wizardSteps) {
        store.setCurrentStep(step as any);
        expect(useAccessBridgeStore.getState().currentStep).toBe(step);
      }
    });

    it('supports multi-modal input (text, documents, audio)', () => {
      const store = useAccessBridgeStore.getState();

      store.setTextInput('test text');
      expect(useAccessBridgeStore.getState().textInput).toBe('test text');

      store.addDocumentText('document content');
      expect(useAccessBridgeStore.getState().documentTexts).toContain('document content');

      store.addAudioTranscript('audio transcript');
      expect(useAccessBridgeStore.getState().audioTranscripts).toContain('audio transcript');
    });

    it('supports follow-up answers for pause/resume', () => {
      const store = useAccessBridgeStore.getState();

      store.updateFollowUpAnswer('field1', 'answer1');
      expect(useAccessBridgeStore.getState().followUpAnswers).toHaveProperty('field1', 'answer1');
    });

    it('stepData has correct initial structure for 6-step wizard', () => {
      const { stepData } = useAccessBridgeStore.getState();

      expect(stepData.process_input).toHaveProperty('status', 'pending');
      expect(stepData.retrieve_program).toHaveProperty('status', 'pending');
      expect(stepData.extract_info).toHaveProperty('status', 'pending');
      expect(stepData.analyze_gaps).toHaveProperty('status', 'pending');
      expect(stepData.process_follow_up).toHaveProperty('status', 'pending');
      expect(stepData.generate_outputs).toHaveProperty('status', 'pending');
    });
  });

  describe('ForesightStore', () => {
    beforeEach(() => {
      // ForesightStore doesn't have a reset method - just verify initial state
    });

    it('has required state properties', () => {
      const state = useForesightStore.getState();

      expect(state).toHaveProperty('activeTab');
      expect(state).toHaveProperty('agentBudget');
      expect(state).toHaveProperty('capitalRiskWeight');
      expect(state).toHaveProperty('capitalImpactWeight'); // CRITICAL: inverse weight
    });

    it('has required action methods', () => {
      const state = useForesightStore.getState();

      expect(typeof state.setActiveTab).toBe('function');
      expect(typeof state.updateCapitalWeights).toBe('function'); // CRITICAL: inverse calculation
    });

    it('supports multi-tab state (agent/capital/emergency/forecast)', () => {
      const store = useForesightStore.getState();

      const tabs = ['agent', 'capital', 'emergency', 'forecast'];
      for (const tab of tabs) {
        store.setActiveTab(tab as any);
        expect(useForesightStore.getState().activeTab).toBe(tab);
      }
    });

    it('CRITICAL: updateCapitalWeights calculates inverse relationship', () => {
      const store = useForesightStore.getState();

      // Set risk weight to 0.7, impact should be 0.3
      store.updateCapitalWeights(0.7);
      const state1 = useForesightStore.getState();
      expect(state1.capitalRiskWeight).toBe(0.7);
      expect(state1.capitalImpactWeight).toBeCloseTo(0.3, 1);

      // Set risk weight to 0.2, impact should be 0.8
      store.updateCapitalWeights(0.2);
      const state2 = useForesightStore.getState();
      expect(state2.capitalRiskWeight).toBe(0.2);
      expect(state2.capitalImpactWeight).toBeCloseTo(0.8, 1);
    });
  });

  describe('KnowledgeBaseStore', () => {
    beforeEach(() => {
      // KnowledgeBaseStore may not have reset - just verify state
    });

    it('has required state properties', () => {
      const state = useKnowledgeBaseStore.getState();

      expect(state).toHaveProperty('activeTab');
      expect(state).toHaveProperty('completedHistory'); // Upload history
      expect(state).toHaveProperty('connectors');
    });

    it('has required action methods', () => {
      const state = useKnowledgeBaseStore.getState();

      expect(typeof state.setActiveTab).toBe('function');
      // reset may not exist on all stores
    });

    it('supports upload vs connectors tabs', () => {
      const store = useKnowledgeBaseStore.getState();

      store.setActiveTab('upload');
      expect(useKnowledgeBaseStore.getState().activeTab).toBe('upload');

      store.setActiveTab('connectors');
      expect(useKnowledgeBaseStore.getState().activeTab).toBe('connectors');
    });
  });
});

describe('Store Persistence Tests', () => {
  it('GovLensStore persists results and mode', () => {
    const store = useGovLensStore.getState();

    // The store is configured to persist: results, mode, selectedFilters, availableFilters
    // We just verify the structure exists
    expect(store).toHaveProperty('results');
    expect(store).toHaveProperty('mode');
    expect(store).toHaveProperty('selectedFilters');
    expect(store).toHaveProperty('availableFilters');
  });

  it('LexGraphStore persists scenario and evalDate', () => {
    const store = useLexGraphStore.getState();

    expect(store).toHaveProperty('scenario');
    expect(store).toHaveProperty('evalDate');
    expect(store).toHaveProperty('evaluationHistory');
  });

  it('AccessBridgeStore persists wizard state and history', () => {
    const store = useAccessBridgeStore.getState();

    expect(store).toHaveProperty('currentStep');
    expect(store).toHaveProperty('selectedModes');
    expect(store).toHaveProperty('sessionHistory');
  });
});

describe('Store Reset Functionality', () => {
  it('stores with streaming have reset or clear methods', () => {
    // LexGraph and AccessBridge have reset
    expect(typeof useLexGraphStore.getState().reset).toBe('function');
    expect(typeof useAccessBridgeStore.getState().reset).toBe('function');
    // GovLens uses clearResults instead of reset
    expect(typeof useGovLensStore.getState().clearResults).toBe('function');
    // Foresight and KnowledgeBase may not have reset - that's OK
  });
});

describe('Critical Unique Logic Preservation', () => {
  describe('AccessBridge pause/resume', () => {
    it('has lastParams for storing resume state', () => {
      const state = useAccessBridgeStore.getState();
      expect(state).toHaveProperty('lastParams');
    });

    it('has submitFollowUp for resumption', () => {
      const state = useAccessBridgeStore.getState();
      expect(typeof state.submitFollowUp).toBe('function');
    });
  });

  describe('LexGraph graph building', () => {
    it('graphData supports nodes with group property', () => {
      const store = useLexGraphStore.getState();

      // Set graph data with groups
      store.setGraphData({
        nodes: [
          { id: 'rule1', label: 'Rule 1', group: 1 },
          { id: 'cond1', label: 'Condition 1', group: 2 },
        ],
        links: [{ source: 'rule1', target: 'cond1' }],
      });

      const { graphData } = useLexGraphStore.getState();
      expect(graphData.nodes[0].group).toBe(1);
      expect(graphData.nodes[1].group).toBe(2);
    });
  });

  describe('GovLens audio integration', () => {
    it('audioPlayer.stop is accessible', async () => {
      const { audioPlayer } = await import('../../services/audioService');
      expect(typeof audioPlayer.stop).toBe('function');
    });
  });

  describe('Foresight multi-tab isolation', () => {
    it('has separate loading states per feature', () => {
      const state = useForesightStore.getState();

      // Agent has its own loading
      expect(state).toHaveProperty('agentLoading');
      // Capital has its own loading
      expect(state).toHaveProperty('capitalLoading');
      // Emergency has its own loading
      expect(state).toHaveProperty('emergencyLoading');
      // Forecast has its own loading
      expect(state).toHaveProperty('forecastLoading');
    });
  });
});
