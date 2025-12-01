import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import {
  StepStatus,
  AccessBridgeStepData,
  AccessBridgeStreamEvent,
  AccessBridgeNodeName,
  AccessBridgeResult,
  ExtractedFieldEnhanced,
  InformationGap,
} from '../types';
import { OutputMode } from '../components/AccessBridge/types';
import { streamWithCallback } from '../services/apiClient';
import { HISTORY_LIMITS, createCancelHandler, createHistoryItem } from './utils/streamingHelpers';
import { debugLog, debugError } from '../utils/debugLogger';

const NODE_ORDER: AccessBridgeNodeName[] = [
  'process_input',
  'retrieve_program',
  'extract_info',
  'analyze_gaps',
  'process_follow_up',
  'generate_outputs',
];

// Initial step data
const initialStepData: AccessBridgeStepData = {
  process_input: { status: 'pending' },
  retrieve_program: { status: 'pending' },
  extract_info: { status: 'pending', fieldsExtracted: 0 },
  analyze_gaps: { status: 'pending', gapsFound: 0, criticalGaps: 0 },
  process_follow_up: { status: 'pending', answersProcessed: 0 },
  generate_outputs: { status: 'pending', outputsReady: [] },
};

// Wizard step type
export type WizardStep = 'mode' | 'input' | 'processing' | 'gaps' | 'output';

// Session history item
export interface AccessBridgeSession {
  id: string;
  timestamp: string;
  textInput: string;
  programType: string;
  result: AccessBridgeResult | null;
}

// Form template for PDF form-driven extraction
export interface FormTemplate {
  pdfBase64: string;
  formName: string;
  fields: Array<{ name: string; type: string; label: string; options?: string[]; required: boolean }>;
  field_groups?: Array<{ group_name: string; group_label: string; group_type: string; options: Array<{ name: string; label: string }>; required: boolean }>;
}

// Process params interface
export interface AccessBridgeProcessParams {
  rawTextInput: string;
  programType: string;
  language: string;  // Output language for final results (email, meeting prep, etc.)
  uiLanguage?: string;  // UI language for gap questions (defaults to language if not provided)
  documentTexts?: string[];
  audioTranscripts?: string[];
  followUpAnswers?: Record<string, string>[];
  formTemplate?: FormTemplate;  // Optional PDF form template for form-driven extraction
  selectedModes?: OutputMode[];  // Which outputs to generate (form, email, meeting)
}

interface AccessBridgeState {
  // Wizard state
  currentStep: WizardStep;
  selectedModes: OutputMode[];  // Which outputs user selected (form, email, meeting)

  // Input state
  textInput: string;
  documentTexts: string[];
  audioTranscripts: string[];

  // Processing state
  stepData: AccessBridgeStepData;
  traceLog: string[];
  loading: boolean;
  error: string | null;

  // Results
  extractedFields: ExtractedFieldEnhanced[];
  gaps: InformationGap[];
  followUpQuestions: string[];
  followUpAnswers: Record<string, string>;
  hasCriticalGaps: boolean;
  result: AccessBridgeResult | null;

  // Audio state (not persisted)
  speaking: boolean;
  audioLoading: boolean;

  // Accumulated history
  sessionHistory: AccessBridgeSession[];

  // AbortController for background requests (not persisted)
  abortController: AbortController | null;

  // Last params for follow-up resumption
  lastParams: AccessBridgeProcessParams | null;
}

interface AccessBridgeActions {
  // Wizard actions
  setCurrentStep: (step: WizardStep) => void;
  setSelectedModes: (modes: OutputMode[]) => void;
  toggleMode: (mode: OutputMode) => void;

  // Input actions
  setTextInput: (text: string) => void;
  setDocumentTexts: (texts: string[]) => void;
  addDocumentText: (text: string) => void;
  setAudioTranscripts: (transcripts: string[]) => void;
  addAudioTranscript: (transcript: string) => void;

  // Processing actions
  setStepData: (stepData: AccessBridgeStepData) => void;
  updateStepData: (updater: (prev: AccessBridgeStepData) => AccessBridgeStepData) => void;
  setTraceLog: (log: string[]) => void;
  appendTraceLog: (logs: string[]) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;

  // Results actions
  setExtractedFields: (fields: ExtractedFieldEnhanced[]) => void;
  setGaps: (gaps: InformationGap[]) => void;
  setFollowUpQuestions: (questions: string[]) => void;
  setFollowUpAnswers: (answers: Record<string, string>) => void;
  updateFollowUpAnswer: (field: string, answer: string) => void;
  setHasCriticalGaps: (hasCriticalGaps: boolean) => void;
  setResult: (result: AccessBridgeResult | null) => void;

  // Audio actions
  setSpeaking: (speaking: boolean) => void;
  setAudioLoading: (loading: boolean) => void;

  // History actions
  addSessionToHistory: (session: Omit<AccessBridgeSession, 'id' | 'timestamp'>) => void;
  clearHistory: () => void;

  // Reset
  reset: () => void;

  // Background-safe process actions
  performProcess: (params: AccessBridgeProcessParams) => Promise<void>;
  submitFollowUp: (answers: Record<string, string>) => Promise<void>;
  cancelProcess: () => void;
}

const initialState: AccessBridgeState = {
  currentStep: 'mode',
  selectedModes: [],
  textInput: '',
  documentTexts: [],
  audioTranscripts: [],
  stepData: initialStepData,
  traceLog: [],
  loading: false,
  error: null,
  extractedFields: [],
  gaps: [],
  followUpQuestions: [],
  followUpAnswers: {},
  hasCriticalGaps: false,
  result: null,
  speaking: false,
  audioLoading: false,
  sessionHistory: [],
  abortController: null,
  lastParams: null,
};

export const useAccessBridgeStore = create<AccessBridgeState & AccessBridgeActions>()(
  persist(
    (set, get) => ({
      ...initialState,

      // Wizard actions
      setCurrentStep: (currentStep) => set({ currentStep }),
      setSelectedModes: (selectedModes) => set({ selectedModes }),
      toggleMode: (mode) =>
        set((state) => ({
          selectedModes: state.selectedModes.includes(mode)
            ? state.selectedModes.filter((m) => m !== mode)
            : [...state.selectedModes, mode],
        })),

      // Input actions
      setTextInput: (textInput) => set({ textInput }),
      setDocumentTexts: (documentTexts) => set({ documentTexts }),
      addDocumentText: (text) =>
        set((state) => ({ documentTexts: [...state.documentTexts, text] })),
      setAudioTranscripts: (audioTranscripts) => set({ audioTranscripts }),
      addAudioTranscript: (transcript) =>
        set((state) => ({ audioTranscripts: [...state.audioTranscripts, transcript] })),

      // Processing actions
      setStepData: (stepData) => set({ stepData }),
      updateStepData: (updater) =>
        set((state) => ({ stepData: updater(state.stepData) })),
      setTraceLog: (traceLog) => set({ traceLog }),
      appendTraceLog: (logs) =>
        set((state) => ({ traceLog: [...state.traceLog, ...logs] })),
      setLoading: (loading) => set({ loading }),
      setError: (error) => set({ error }),

      // Results actions
      setExtractedFields: (extractedFields) => set({ extractedFields }),
      setGaps: (gaps) => set({ gaps }),
      setFollowUpQuestions: (followUpQuestions) => set({ followUpQuestions }),
      setFollowUpAnswers: (followUpAnswers) => set({ followUpAnswers }),
      updateFollowUpAnswer: (field, answer) =>
        set((state) => ({
          followUpAnswers: { ...state.followUpAnswers, [field]: answer },
        })),
      setHasCriticalGaps: (hasCriticalGaps) => set({ hasCriticalGaps }),
      setResult: (result) => set({ result }),

      // Audio actions
      setSpeaking: (speaking) => set({ speaking }),
      setAudioLoading: (audioLoading) => set({ audioLoading }),

      // History actions
      addSessionToHistory: (session) =>
        set((state) => ({
          sessionHistory: [
            ...state.sessionHistory,
            createHistoryItem(session),
          ].slice(-HISTORY_LIMITS.ACCESS_SESSIONS),
        })),

      clearHistory: () => set({ sessionHistory: [] }),

      // Reset
      reset: () =>
        set({
          currentStep: 'mode',
          selectedModes: [],
          textInput: '',
          documentTexts: [],
          audioTranscripts: [],
          stepData: initialStepData,
          traceLog: [],
          loading: false,
          error: null,
          extractedFields: [],
          gaps: [],
          followUpQuestions: [],
          followUpAnswers: {},
          hasCriticalGaps: false,
          result: null,
          speaking: false,
          audioLoading: false,
          lastParams: null,
        }),

      cancelProcess: createCancelHandler(get, set),

      performProcess: async (params: AccessBridgeProcessParams) => {
        // Abort any existing request
        get().abortController?.abort();
        const controller = new AbortController();

        // Store params for follow-up
        set({ lastParams: params });

        // Reset state
        set({
          abortController: controller,
          stepData: initialStepData,
          traceLog: [],
          result: null,
          error: null,
          extractedFields: [],
          gaps: [],
          followUpQuestions: [],
          hasCriticalGaps: false,
          loading: true,
        });

        // Mark first step as in_progress
        set((state) => ({
          stepData: {
            ...state.stepData,
            process_input: { ...state.stepData.process_input, status: 'in_progress' as StepStatus },
          },
        }));

        // Track extracted data for final result
        let latestExtractedFields: ExtractedFieldEnhanced[] = [];
        let latestGaps: InformationGap[] = [];

        // Define event handler for stream events
        const handleEvent = (event: AccessBridgeStreamEvent) => {
          const { node, state: eventState } = event;
          debugLog(`[AccessBridge] Node completed: ${node}`, eventState);

          // Accumulate trace log
          if (eventState.trace_log) {
            set((s) => ({ traceLog: [...s.traceLog, ...eventState.trace_log] }));
          }

          // Update the completed node's data
          set((currentState) => {
            const updated = { ...currentState.stepData };

            if (node === 'process_input') {
              updated.process_input = {
                status: 'completed',
                filesProcessed: (eventState.document_texts?.length || 0) + (eventState.audio_transcripts?.length || 0),
              };
            } else if (node === 'retrieve_program') {
              updated.retrieve_program = {
                status: 'completed',
                programName: eventState.program_type,
                requiredFields: eventState.required_fields,
              };
            } else if (node === 'extract_info') {
              const fields = (eventState.extracted_fields || []) as ExtractedFieldEnhanced[];
              latestExtractedFields = fields;
              set({ extractedFields: fields });
              updated.extract_info = {
                status: 'completed',
                fieldsExtracted: fields.length,
              };
            } else if (node === 'analyze_gaps') {
              const infoGaps = (eventState.information_gaps || []) as InformationGap[];
              const questions = eventState.follow_up_questions || [];
              const criticalCount = infoGaps.filter((g) => g.priority === 'critical').length;

              latestGaps = infoGaps;
              set({
                gaps: infoGaps,
                followUpQuestions: questions,
                hasCriticalGaps: eventState.has_critical_gaps || false,
              });

              updated.analyze_gaps = {
                status: 'completed',
                gapsFound: infoGaps.length,
                criticalGaps: criticalCount,
              };

              // If waiting for input (has critical gaps), don't mark further steps
              if (eventState.completion_status === 'needs_input') {
                set({ loading: false });
                return { stepData: updated };
              }
            } else if (node === 'process_follow_up') {
              const fields = (eventState.extracted_fields || []) as ExtractedFieldEnhanced[];
              latestExtractedFields = fields;
              set({ extractedFields: fields });
              updated.process_follow_up = {
                status: 'completed',
                answersProcessed: get().lastParams?.followUpAnswers?.length || 0,
              };
            } else if (node === 'generate_outputs') {
              const outputsReady: string[] = [];
              if (eventState.form_data) outputsReady.push('form');
              if (eventState.email_draft) outputsReady.push('email');
              if (eventState.meeting_prep) outputsReady.push('meeting');

              updated.generate_outputs = {
                status: 'completed',
                outputsReady,
              };

              // Set final result using tracked values
              const finalResult: AccessBridgeResult = {
                extractedFields: latestExtractedFields,
                gaps: latestGaps,
                formData: eventState.form_data || {},
                emailDraft: eventState.email_draft || '',
                meetingPrep: eventState.meeting_prep || '',
                confidence: eventState.overall_confidence || 0,
                status: eventState.completion_status || 'complete',
              };
              set({ result: finalResult });

              // Add to history
              get().addSessionToHistory({
                textInput: params.rawTextInput,
                programType: params.programType,
                result: finalResult,
              });
            } else if (node === 'error') {
              // Handle API key required and other errors
              const errorMessage = eventState.message || eventState.trace_log?.[0] || 'Unknown error';
              set({ error: errorMessage });
            }

            // Mark next node as in_progress
            const nodeIdx = NODE_ORDER.indexOf(node as AccessBridgeNodeName);
            if (nodeIdx >= 0 && nodeIdx < NODE_ORDER.length - 1) {
              const nextNode = NODE_ORDER[nodeIdx + 1];
              (updated as any)[nextNode] = { ...(updated as any)[nextNode], status: 'in_progress' as StepStatus };
            }

            return { stepData: updated };
          });
        };

        try {
          await streamWithCallback<AccessBridgeStreamEvent>(
            '/agent/accessbridge/stream',
            {
              raw_text_input: params.rawTextInput,
              program_type: params.programType,
              language: params.language,  // Output language for final results
              ui_language: params.uiLanguage || null,  // UI language for gap questions
              document_texts: params.documentTexts || null,
              audio_transcripts: params.audioTranscripts || null,
              follow_up_answers: params.followUpAnswers || null,
              // Pass form template for form-driven extraction
              form_template: params.formTemplate ? {
                pdfBase64: params.formTemplate.pdfBase64,
                formName: params.formTemplate.formName,
                fields: params.formTemplate.fields,
                field_groups: params.formTemplate.field_groups,  // Include grouped fields
              } : null,
              // Pass selected output modes
              selected_modes: params.selectedModes || null,
            },
            handleEvent,
            controller.signal
          );
        } catch (e) {
          if (controller.signal.aborted) return;
          debugError('AccessBridge processing error:', e);
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

      submitFollowUp: async (answers: Record<string, string>) => {
        const lastParams = get().lastParams;
        if (!lastParams) {
          set({ error: 'No previous session to resume' });
          return;
        }

        // Convert answers object to array format expected by backend
        const answersArray = [answers];

        // Resume with follow-up answers
        await get().performProcess({
          ...lastParams,
          followUpAnswers: answersArray,
        });
      },
    }),
    {
      name: 'accessbridge-session',
      storage: createJSONStorage(() => sessionStorage),
      // Only persist these fields
      partialize: (state) => ({
        currentStep: state.currentStep,
        selectedModes: state.selectedModes,
        textInput: state.textInput,
        documentTexts: state.documentTexts,
        audioTranscripts: state.audioTranscripts,
        followUpAnswers: state.followUpAnswers,
        result: state.result,
        sessionHistory: state.sessionHistory,
      }),
    }
  )
);

// Export initial step data for use in hooks
export { initialStepData };
