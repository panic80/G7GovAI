import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { SearchResult, SearchMode, RagResponse, GovLensResponseStream, Language } from '../types';
import { FilterOptions, searchKnowledgeBase } from '../services/ragService';
import { streamGovLensSearch } from '../services/geminiService';
import { audioPlayer } from '../services/audioService';
import { HISTORY_LIMITS } from './utils/streamingHelpers';
import { debugError } from '../utils/debugLogger';

export interface ChatMessage {
  role: 'user' | 'model';
  content: string;
}

export interface SearchFilters {
  categories: string[];
}

// Q&A pair for storing query + result together
export interface QAPair {
  query: string;
  result: SearchResult;
  timestamp: string;
}

interface GovLensState {
  // Current session state
  query: string;
  loading: boolean;
  currentQuery: string; // Track current query while loading
  results: QAPair[]; // Array of Q&A pairs
  streamingTrace: string[];
  mode: SearchMode;

  // Filter state
  selectedFilters: SearchFilters;
  availableFilters: FilterOptions;
  filtersLoading: boolean;

  // AbortController for background requests (not persisted)
  abortController: AbortController | null;
}

interface GovLensActions {
  setQuery: (query: string) => void;
  setLoading: (loading: boolean) => void;
  setResults: (results: QAPair[]) => void;
  clearResults: () => void;
  setStreamingTrace: (traceOrUpdater: string[] | ((prev: string[]) => string[])) => void;
  setMode: (mode: SearchMode) => void;
  setSelectedFilters: (filters: SearchFilters) => void;
  updateFilters: (filters: Partial<SearchFilters>) => void;
  clearFilters: () => void;
  setAvailableFilters: (filters: FilterOptions) => void;
  setFiltersLoading: (loading: boolean) => void;

  // Background-safe search actions
  performSearch: (query: string, language: string) => Promise<void>;
  cancelSearch: () => void;
}

const initialState: GovLensState = {
  query: '',
  loading: false,
  currentQuery: '',
  results: [],
  streamingTrace: [],
  mode: 'rag',
  selectedFilters: { categories: [] },
  availableFilters: { categories: [], themes: [] },
  filtersLoading: false,
  abortController: null,
};

export const useGovLensStore = create<GovLensState & GovLensActions>()(
  persist(
    (set, get) => ({
      ...initialState,

      setQuery: (query) => set({ query }),
      setLoading: (loading) => set({ loading }),
      setResults: (results) => set({ results }),
      clearResults: () => set({ results: [], streamingTrace: [], currentQuery: '' }),

      setStreamingTrace: (traceOrUpdater) =>
        set((state) => ({
          streamingTrace: typeof traceOrUpdater === 'function'
            ? traceOrUpdater(state.streamingTrace)
            : traceOrUpdater,
        })),
      setMode: (mode) => set({ mode }),
      setSelectedFilters: (filters) => set({ selectedFilters: filters }),

      updateFilters: (filters) =>
        set((state) => ({
          selectedFilters: { ...state.selectedFilters, ...filters },
        })),

      clearFilters: () => set({ selectedFilters: { categories: [] } }),
      setAvailableFilters: (filters) => set({ availableFilters: filters }),
      setFiltersLoading: (loading) => set({ filtersLoading: loading }),

      cancelSearch: () => {
        const controller = get().abortController;
        if (controller) {
          controller.abort();
          set({ abortController: null, loading: false });
        }
      },

      performSearch: async (currentQuery: string, language: string) => {
        // Abort any existing request
        get().abortController?.abort();
        const controller = new AbortController();

        // Stop any existing audio
        audioPlayer.stop();

        // Reset state and start loading
        set({
          abortController: controller,
          loading: true,
          streamingTrace: [],
          query: '', // Clear input
          currentQuery, // Track current query for display while loading
        });

        const { mode, selectedFilters } = get();
        const hasActiveFilters = selectedFilters.categories.length > 0;

        try {
          if (mode === 'rag') {
            // --- RAG MODE ---
            const ragFilters = hasActiveFilters
              ? { categories: selectedFilters.categories.length > 0 ? selectedFilters.categories : undefined }
              : undefined;

            // Track if we've already processed the final answer to prevent duplicates
            let hasProcessedFinalAnswer = false;

            await streamGovLensSearch(
              currentQuery,
              language,
              (newState: GovLensResponseStream) => {
                if (controller.signal.aborted) return;
                set({ streamingTrace: newState.trace_log });

                // Only process final_answer ONCE (streaming accumulates state, so this fires multiple times)
                if (newState.final_answer && !hasProcessedFinalAnswer) {
                  hasProcessedFinalAnswer = true;
                  try {
                    let finalResult: RagResponse = JSON.parse(newState.final_answer);

                    // Handle nested JSON from backend fallback
                    if (
                      typeof finalResult.answer === 'string' &&
                      finalResult.answer.trim().startsWith('{')
                    ) {
                      try {
                        const innerJson = JSON.parse(finalResult.answer);
                        if (innerJson && innerJson.answer) {
                          finalResult = {
                            ...finalResult,
                            ...innerJson,
                            citations: Array.isArray(innerJson.citations) ? innerJson.citations : finalResult.citations,
                            bullets: Array.isArray(innerJson.bullets) ? innerJson.bullets : finalResult.bullets,
                          };
                        }
                      } catch {
                        /* Ignore invalid inner JSON */
                      }
                    }

                    finalResult.type = 'rag';

                    // Add Q&A pair to results array
                    set((state) => ({
                      results: [...state.results, {
                        query: currentQuery,
                        result: finalResult,
                        timestamp: new Date().toISOString(),
                      }].slice(-HISTORY_LIMITS.QA_PAIRS),
                      currentQuery: '', // Clear current query
                    }));
                  } catch (e) {
                    debugError('Error parsing final GovLens answer:', e);
                  }
                }
              },
              controller.signal,
              ragFilters
            );
          } else {
            // --- SEMANTIC MODE ---
            set((state) => ({ streamingTrace: ['Initiating Semantic Search (No LLM)...'] }));

            const semanticFilters = hasActiveFilters
              ? { categories: selectedFilters.categories.length > 0 ? selectedFilters.categories : undefined }
              : undefined;

            const chunks = await searchKnowledgeBase(
              currentQuery,
              language as Language,
              undefined,
              undefined,
              semanticFilters
            );

            if (controller.signal.aborted) return;

            // Add Q&A pair to results array
            set((state) => ({
              results: [...state.results, {
                query: currentQuery,
                result: { type: 'semantic' as const, results: chunks },
                timestamp: new Date().toISOString(),
              }].slice(-HISTORY_LIMITS.QA_PAIRS),
              streamingTrace: ['Initiating Semantic Search (No LLM)...', `Found ${chunks.length} documents.`],
              currentQuery: '', // Clear current query
            }));
          }
        } catch (err: unknown) {
          if (controller.signal.aborted || (err as Error)?.name === 'AbortError') {
            return;
          }
          debugError(err);
          set((state) => ({
            streamingTrace: [...state.streamingTrace, `Error: ${String(err)}`],
            currentQuery: '', // Clear current query on error
          }));
        } finally {
          if (!controller.signal.aborted) {
            set({ loading: false });
          }
        }
      },
    }),
    {
      name: 'govlens-session',
      storage: createJSONStorage(() => sessionStorage),
      // Only persist these fields (not loading states or streaming trace)
      partialize: (state) => ({
        results: state.results,
        mode: state.mode,
        selectedFilters: state.selectedFilters,
        availableFilters: state.availableFilters,
      }),
    }
  )
);
