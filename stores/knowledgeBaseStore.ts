import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { HISTORY_LIMITS } from './utils/streamingHelpers';
import type {
  UploadHistoryItem,
  IngestionLog,
  UploadStatus,
  IngestionStep,
  Connector,
  Dataset,
  ImportProgressState,
  KnowledgeBaseStats,
} from '../components/KnowledgeBase/types';

// Tab type
export type KnowledgeBaseTab = 'upload' | 'connectors';

interface KnowledgeBaseState {
  // Tab state
  activeTab: KnowledgeBaseTab;

  // Upload state (Note: File objects cannot be persisted)
  uploadStatus: UploadStatus;
  currentStep: IngestionStep;
  progress: number;
  message: string;
  showLogs: boolean;
  logs: IngestionLog[];
  stepModels: Record<IngestionStep, string>;

  // Upload history (persisted)
  completedHistory: UploadHistoryItem[];

  // Connectors state
  connectors: Record<string, Connector[]>;
  connectorsLoading: boolean;
  selectedConnector: string | null;
  datasets: Dataset[];
  datasetsLoading: boolean;
  importProgress: ImportProgressState | null;
  expandedCountry: string | null;

  // Stats (cached)
  stats: KnowledgeBaseStats | null;
  statsLoading: boolean;
  purging: boolean;
}

interface KnowledgeBaseActions {
  // Tab actions
  setActiveTab: (tab: KnowledgeBaseTab) => void;

  // Upload actions
  setUploadStatus: (status: UploadStatus) => void;
  setCurrentStep: (step: IngestionStep) => void;
  setProgress: (progress: number) => void;
  setMessage: (message: string) => void;
  setShowLogs: (show: boolean) => void;
  setLogs: (logs: IngestionLog[]) => void;
  addLog: (log: IngestionLog) => void;
  clearLogs: () => void;
  setStepModel: (step: IngestionStep, model: string) => void;

  // History actions
  setCompletedHistory: (history: UploadHistoryItem[]) => void;
  addToCompletedHistory: (item: UploadHistoryItem) => void;
  clearCompletedHistory: () => void;

  // Connectors actions
  setConnectors: (connectors: Record<string, Connector[]>) => void;
  setConnectorsLoading: (loading: boolean) => void;
  setSelectedConnector: (connector: string | null) => void;
  setDatasets: (datasets: Dataset[]) => void;
  setDatasetsLoading: (loading: boolean) => void;
  setImportProgress: (progress: ImportProgressState | null) => void;
  setExpandedCountry: (country: string | null) => void;
  toggleCountry: (country: string) => void;

  // Stats actions
  setStats: (stats: KnowledgeBaseStats | null) => void;
  setStatsLoading: (loading: boolean) => void;
  setPurging: (purging: boolean) => void;

  // Reset upload state (for new uploads)
  resetUpload: () => void;
}

const initialState: KnowledgeBaseState = {
  activeTab: 'upload',

  // Upload state
  uploadStatus: 'idle',
  currentStep: 'reading',
  progress: 0,
  message: '',
  showLogs: false,
  logs: [],
  stepModels: {
    reading: '',
    analyzing: '',
    embedding: '',
    complete: '',
  },

  // History
  completedHistory: [],

  // Connectors
  connectors: {},
  connectorsLoading: false,
  selectedConnector: null,
  datasets: [],
  datasetsLoading: false,
  importProgress: null,
  expandedCountry: null,

  // Stats
  stats: null,
  statsLoading: false,
  purging: false,
};

export const useKnowledgeBaseStore = create<KnowledgeBaseState & KnowledgeBaseActions>()(
  persist(
    (set) => ({
      ...initialState,

      // Tab actions
      setActiveTab: (activeTab) => set({ activeTab }),

      // Upload actions
      setUploadStatus: (uploadStatus) => set({ uploadStatus }),
      setCurrentStep: (currentStep) => set({ currentStep }),
      setProgress: (progress) => set({ progress }),
      setMessage: (message) => set({ message }),
      setShowLogs: (showLogs) => set({ showLogs }),
      setLogs: (logs) => set({ logs }),
      addLog: (log) => set((state) => ({ logs: [...state.logs, log] })),
      clearLogs: () => set({ logs: [] }),
      setStepModel: (step, model) => set((state) => ({
        stepModels: { ...state.stepModels, [step]: model }
      })),

      // History actions
      setCompletedHistory: (completedHistory) => set({ completedHistory }),
      addToCompletedHistory: (item) =>
        set((state) => ({
          completedHistory: [...state.completedHistory, item].slice(-HISTORY_LIMITS.UPLOAD_HISTORY),
        })),
      clearCompletedHistory: () => set({ completedHistory: [] }),

      // Connectors actions
      setConnectors: (connectors) => set({ connectors }),
      setConnectorsLoading: (connectorsLoading) => set({ connectorsLoading }),
      setSelectedConnector: (selectedConnector) => set({ selectedConnector }),
      setDatasets: (datasets) => set({ datasets }),
      setDatasetsLoading: (datasetsLoading) => set({ datasetsLoading }),
      setImportProgress: (importProgress) => set({ importProgress }),
      setExpandedCountry: (expandedCountry) => set({ expandedCountry }),
      toggleCountry: (country) =>
        set((state) => ({
          expandedCountry: state.expandedCountry === country ? null : country,
        })),

      // Stats actions
      setStats: (stats) => set({ stats }),
      setStatsLoading: (statsLoading) => set({ statsLoading }),
      setPurging: (purging) => set({ purging }),

      // Reset upload state
      resetUpload: () =>
        set({
          uploadStatus: 'idle',
          currentStep: 'reading',
          progress: 0,
          message: '',
          logs: [],
          stepModels: {
            reading: '',
            analyzing: '',
            embedding: '',
            complete: '',
          },
        }),
    }),
    {
      name: 'knowledgebase-session',
      storage: createJSONStorage(() => sessionStorage),
      // Only persist these fields (not loading states or progress)
      partialize: (state) => ({
        activeTab: state.activeTab,
        completedHistory: state.completedHistory,
        connectors: state.connectors,
        selectedConnector: state.selectedConnector,
        expandedCountry: state.expandedCountry,
        stats: state.stats,
      }),
    }
  )
);
