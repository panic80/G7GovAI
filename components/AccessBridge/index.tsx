import React, { useState, useCallback, useEffect, useMemo } from 'react';
import { Users, Eye, EyeOff, Type } from 'lucide-react';
import { Language, G7_LANGUAGES, translations } from '../../contexts/LanguageContext';
import { useAccessibility } from '../../contexts/AccessibilityContext';
import { useAccessBridgeStream } from '../../hooks/useAccessBridgeStream';
import { useSpeech } from '../../hooks/useSpeech';

// Components
import {
  WizardProgressBar,
  ModeStep,
  InputStep,
  ProcessingStep,
  GapsStep,
  OutputStep,
  FormUpload,
} from './components';
import { CONFIG } from '../../config';

// Types
import type { WizardStep, OutputMode } from './types';

export const AccessBridge: React.FC = () => {
  const { settings, toggleHighContrast, setFontSize } = useAccessibility();

  // Local language state for AccessBridge only (does not affect global app language)
  const [accessBridgeLanguage, setAccessBridgeLanguage] = useState<Language>(Language.EN);
  const [outputLanguage, setOutputLanguage] = useState<Language>(Language.EN);

  // Local translation function for AccessBridge content only
  const tLocal = useMemo(() => {
    return (key: string): string => {
      return translations[accessBridgeLanguage]?.[key] || key;
    };
  }, [accessBridgeLanguage]);

  // Wizard state
  const [currentStep, setCurrentStep] = useState<WizardStep>('mode');
  const [selectedModes, setSelectedModes] = useState<OutputMode[]>([]);

  // Input state
  const [textInput, setTextInput] = useState('');
  const [documentTexts, setDocumentTexts] = useState<string[]>([]);
  const [audioTranscripts, setAudioTranscripts] = useState<string[]>([]);

  // Form template state (for PDF form filling)
  const [formTemplate, setFormTemplate] = useState<{
    pdfBase64: string;
    formName: string;
    fields: Array<{ name: string; type: string; label: string; options?: string[]; required: boolean }>;
    field_groups?: Array<{ group_name: string; group_label: string; group_type: string; options: Array<{ name: string; label: string }>; required: boolean }>;
  } | null>(null);

  // Filled form state
  const [filledForm, setFilledForm] = useState<{
    pdfBase64: string;
    fieldMapping: Record<string, { value: string; source?: string; confidence?: number }>;
    fieldsFilled: number;
    unmappedFields: string[];
    unusedData: string[];
  } | null>(null);
  const [isFillingForm, setIsFillingForm] = useState(false);

  // Follow-up state
  const [followUpAnswers, setFollowUpAnswers] = useState<Record<string, string>>({});

  // Audio/TTS hook
  const { speaking, loading: audioLoading, speak } = useSpeech();

  // Streaming hook
  const {
    stepData,
    traceLog,
    loading,
    result,
    error,
    gaps,
    hasCriticalGaps,
    process,
    submitFollowUp,
    reset,
  } = useAccessBridgeStream();

  // Start processing
  const handleProcess = async () => {
    setCurrentStep('processing');
    await process({
      rawTextInput: textInput,
      programType: 'auto',
      language: outputLanguage,  // Output language for final results
      uiLanguage: accessBridgeLanguage,  // UI language for gap questions
      documentTexts: documentTexts.length > 0 ? documentTexts : undefined,
      audioTranscripts: audioTranscripts.length > 0 ? audioTranscripts : undefined,
      // Pass form template if uploaded - this drives form-based extraction
      formTemplate: formTemplate ? {
        pdfBase64: formTemplate.pdfBase64,
        formName: formTemplate.formName,
        fields: formTemplate.fields,
        field_groups: formTemplate.field_groups  // Include grouped fields
      } : undefined,
      // Pass selected output modes
      selectedModes: selectedModes.length > 0 ? selectedModes : undefined,
    });
  };

  // Watch for state changes to transition steps
  useEffect(() => {
    if (!loading && currentStep === 'processing') {
      if (hasCriticalGaps && gaps.length > 0) {
        setCurrentStep('gaps');
      } else if (result) {
        setCurrentStep('output');
      }
    }
  }, [loading, hasCriticalGaps, gaps, result, currentStep]);

  // Auto-fill PDF form when result is ready and form template exists
  useEffect(() => {
    const autoFillForm = async () => {
      if (!result || !formTemplate || isFillingForm || filledForm) return;

      setIsFillingForm(true);
      try {
        const response = await fetch(`${CONFIG.RAG.BASE_URL}/form/auto-fill`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            pdf_base64: formTemplate.pdfBase64,
            extracted_data: result.formData,
            language: outputLanguage
          }),
        });

        if (response.ok) {
          const data = await response.json();
          setFilledForm({
            pdfBase64: data.filled_pdf_base64,
            fieldMapping: data.field_mapping,
            fieldsFilled: data.fields_filled,
            unmappedFields: data.unmapped_fields || [],
            unusedData: data.unused_data || []
          });
        }
      } catch (err) {
        if (import.meta.env.DEV) console.error('Form auto-fill error:', err);
      } finally {
        setIsFillingForm(false);
      }
    };

    autoFillForm();
  }, [result, formTemplate, outputLanguage]);

  // Submit follow-up answers
  const handleSubmitFollowUp = async () => {
    setCurrentStep('processing');
    await submitFollowUp(followUpAnswers);
  };

  // Reset wizard
  const handleReset = () => {
    reset();
    setCurrentStep('mode');
    setSelectedModes([]);
    setTextInput('');
    setDocumentTexts([]);
    setAudioTranscripts([]);
    setFollowUpAnswers({});
    setFormTemplate(null);
    setFilledForm(null);
  };

  // Handle voice transcript
  const handleVoiceTranscript = (text: string) => {
    setAudioTranscripts((prev) => [...prev, text]);
  };

  // Handle file OCR results
  const handleFilesProcessed = useCallback((texts: string[]) => {
    setDocumentTexts(texts);
  }, []);

  // Speak gaps using the useSpeech hook
  const handleSpeakGaps = () => {
    if (gaps.length === 0) return;

    const gapText = accessBridgeLanguage === Language.FR
      ? `Attention. Il manque des informations. ${gaps.map((g) => `Pour le champ ${g.field}, nous avons besoin de : ${g.question}`).join('. ')}`
      : `Attention. Information missing. ${gaps.map((g) => `For ${g.field}, we need: ${g.question}`).join('. ')}`;

    speak(gapText, accessBridgeLanguage);
  };

  // Check if can proceed
  const hasInput = textInput.trim() || documentTexts.length > 0 || audioTranscripts.length > 0;
  const formModeRequiresPdf = selectedModes.includes('form') && !formTemplate;
  const canProcess = hasInput && !formModeRequiresPdf;

  return (
    <div className="max-w-7xl mx-auto p-6 h-[calc(100vh-5rem)]">
      {/* Skip Link for Accessibility */}
      <a
        href="#accessbridge-main"
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-gov-blue focus:text-white focus:rounded-lg"
      >
        {tLocal('access.skipToMain') || 'Skip to main content'}
      </a>

      {/* Header */}
      <header className="mb-6">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
            <Users className="w-8 h-8 text-gov-blue" aria-hidden="true" />
            {tLocal('nav.assist')}
            <span className="text-lg font-normal text-gray-500">| {tLocal('access.subtitle')}</span>
          </h1>

          {/* Accessibility Controls (Language moved to ModeStep) */}
          <div className="flex items-center gap-2" role="group" aria-label={tLocal('access.accessibilityOptions') || 'Accessibility options'}>
            {/* High Contrast Toggle */}
            <button
              onClick={toggleHighContrast}
              className={`flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg transition focus:ring-2 focus:ring-gov-accent focus:ring-offset-2 focus:outline-none ${
                settings.highContrast
                  ? 'bg-gov-blue text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
              aria-pressed={settings.highContrast}
              title={tLocal('access.highContrast') || 'High contrast mode'}
            >
              {settings.highContrast ? (
                <EyeOff className="w-4 h-4" aria-hidden="true" />
              ) : (
                <Eye className="w-4 h-4" aria-hidden="true" />
              )}
              <span className="hidden sm:inline">
                {settings.highContrast
                  ? (tLocal('access.highContrastOn') || 'High Contrast On')
                  : (tLocal('access.highContrastOff') || 'High Contrast')}
              </span>
            </button>

            {/* Font Size Toggle */}
            <div className="flex items-center">
              <button
                onClick={() => {
                  const sizes: Array<'normal' | 'large' | 'xlarge'> = ['normal', 'large', 'xlarge'];
                  const currentIndex = sizes.indexOf(settings.fontSize);
                  setFontSize(sizes[(currentIndex + 1) % sizes.length]);
                }}
                className="flex items-center gap-2 px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition focus:ring-2 focus:ring-gov-accent focus:ring-offset-2 focus:outline-none"
                aria-label={`${tLocal('access.fontSize') || 'Font size'}: ${settings.fontSize}`}
                title={tLocal('access.fontSize') || 'Change font size'}
              >
                <Type className="w-4 h-4" aria-hidden="true" />
                <span className="hidden sm:inline text-xs uppercase">{settings.fontSize}</span>
              </button>
            </div>
          </div>
        </div>
        <p className="text-gray-600 mt-1">
          {tLocal('access.description')}
        </p>
      </header>

      {/* Wizard Progress Bar */}
      <WizardProgressBar currentStep={currentStep} t={tLocal} />

      {/* Main Content */}
      <main
        id="accessbridge-main"
        className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 h-[calc(100%-10rem)] overflow-y-auto"
        role="main"
        aria-labelledby="accessbridge-heading"
      >
        {/* STEP 0: Mode Selection */}
        {currentStep === 'mode' && (
          <ModeStep
            selectedModes={selectedModes}
            onToggleMode={(mode) => setSelectedModes((prev) =>
              prev.includes(mode) ? prev.filter((m) => m !== mode) : [...prev, mode]
            )}
            onContinue={() => setCurrentStep('input')}
            language={accessBridgeLanguage}
            onLanguageChange={(lang) => {
              setAccessBridgeLanguage(lang);
              // Default output language to match UI language when UI language changes
              setOutputLanguage(lang);
            }}
            outputLanguage={outputLanguage}
            onOutputLanguageChange={setOutputLanguage}
            t={tLocal}
          />
        )}

        {/* STEP 1: Input Selection */}
        {currentStep === 'input' && (
          <InputStep
            textInput={textInput}
            setTextInput={setTextInput}
            documentTexts={documentTexts}
            audioTranscripts={audioTranscripts}
            onFilesProcessed={handleFilesProcessed}
            onVoiceTranscript={handleVoiceTranscript}
            onProcess={handleProcess}
            canProcess={canProcess}
            formTemplate={formTemplate}
            onFormUploaded={setFormTemplate}
            onFormClear={() => setFormTemplate(null)}
            selectedModes={selectedModes}
            onBack={() => setCurrentStep('mode')}
            language={accessBridgeLanguage}
            t={tLocal}
          />
        )}

        {/* STEP 2: Processing */}
        {currentStep === 'processing' && (
          <ProcessingStep
            stepData={stepData}
            traceLog={traceLog}
            error={error}
            t={tLocal}
          />
        )}

        {/* STEP 3: Fill Gaps */}
        {currentStep === 'gaps' && (
          <GapsStep
            gaps={gaps}
            followUpAnswers={followUpAnswers}
            setFollowUpAnswers={setFollowUpAnswers}
            speaking={speaking}
            audioLoading={audioLoading}
            onSpeakGaps={handleSpeakGaps}
            onBack={() => setCurrentStep('input')}
            onSubmit={handleSubmitFollowUp}
            t={tLocal}
          />
        )}

        {/* STEP 4: Output Results */}
        {currentStep === 'output' && result && (
          <OutputStep
            result={result}
            onReset={handleReset}
            filledForm={filledForm}
            formName={formTemplate?.formName}
            isFillingForm={isFillingForm}
            selectedModes={selectedModes}
            t={tLocal}
            language={accessBridgeLanguage}
          />
        )}
      </main>
    </div>
  );
};

export default AccessBridge;
