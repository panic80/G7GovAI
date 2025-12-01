import React, { useState, useMemo } from 'react';
import { CheckCircle2, FileText, Mail, Calendar, AlertTriangle, Copy, Check, FileCheck, Loader2 } from 'lucide-react';
import { Language } from '../../../contexts/LanguageContext';
import { COPY_FEEDBACK_MS } from '../../../constants';
import type { OutputTab, OutputMode } from '../types';
import { FormPreview } from './FormPreview';

interface OutputResult {
  confidence: number;
  formData: Record<string, { value: unknown; confidence: number; source?: string }>;
  emailDraft: string;
  meetingPrep: string;
  gaps: Array<{ field: string; question: string }>;
}

interface FilledForm {
  pdfBase64: string;
  fieldMapping: Record<string, { value: string; source?: string; confidence?: number }>;
  fieldsFilled: number;
  unmappedFields: string[];
  unusedData: string[];
}

interface OutputStepProps {
  result: OutputResult;
  onReset: () => void;
  filledForm?: FilledForm | null;
  formName?: string;
  isFillingForm?: boolean;
  selectedModes: OutputMode[];
  t: (key: string) => string;
  language: Language;
}

export const OutputStep: React.FC<OutputStepProps> = ({
  result,
  onReset,
  filledForm,
  formName,
  isFillingForm,
  selectedModes,
  t,
  language,
}) => {

  // Build list of visible tabs based on selectedModes
  const allTabs = useMemo(() => [
    { id: 'form' as const, icon: FileText, labelKey: 'access.tab.form' },
    { id: 'email' as const, icon: Mail, labelKey: 'access.tab.email' },
    { id: 'meeting' as const, icon: Calendar, labelKey: 'access.tab.meeting' },
    // Only show filled tab if a form was uploaded
    ...(filledForm || isFillingForm ? [{ id: 'filled' as const, icon: FileCheck, labelKey: 'access.tab.filled' }] : []),
  ], [filledForm, isFillingForm]);

  // Filter to only show selected modes (filled tab follows form selection)
  const visibleTabs = useMemo(() => {
    return allTabs.filter(tab => {
      if (tab.id === 'filled') return selectedModes.includes('form');
      return selectedModes.includes(tab.id);
    });
  }, [allTabs, selectedModes]);

  // Determine default tab: filled if available and form mode, else first visible tab
  const defaultTab = useMemo(() => {
    if (filledForm && selectedModes.includes('form')) return 'filled';
    return visibleTabs[0]?.id || 'form';
  }, [filledForm, selectedModes, visibleTabs]);

  const [outputTab, setOutputTab] = useState<OutputTab>(defaultTab);
  const [copied, setCopied] = useState(false);

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), COPY_FEEDBACK_MS);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 id="output-heading" className="text-xl font-semibold flex items-center gap-2">
          <CheckCircle2 className="w-6 h-6 text-green-500" aria-hidden="true" />
          {t('access.resultsReady')}
          <span className="text-sm font-normal text-gray-500">
            ({Math.round(result.confidence * 100)}% {t('govlens.confidence')})
          </span>
        </h2>
        <button
          onClick={onReset}
          className="text-sm text-gov-blue hover:underline focus:ring-2 focus:ring-gov-accent focus:ring-offset-2 focus:outline-none rounded"
        >
          {t('access.newRequest')}
        </button>
      </div>

      {/* Output Tabs */}
      <div
        className="flex gap-2 border-b border-gray-200"
        role="tablist"
        aria-label={t('access.outputFormats') || 'Output format options'}
      >
        {visibleTabs.map(({ id, icon: Icon, labelKey }) => (
          <button
            key={id}
            role="tab"
            id={`tab-${id}`}
            aria-selected={outputTab === id}
            aria-controls={`panel-${id}`}
            tabIndex={outputTab === id ? 0 : -1}
            onClick={() => setOutputTab(id)}
            onKeyDown={(e) => {
              const tabIds = visibleTabs.map(t => t.id);
              const currentIndex = tabIds.indexOf(id);
              if (e.key === 'ArrowRight') {
                e.preventDefault();
                setOutputTab(tabIds[(currentIndex + 1) % tabIds.length]);
              } else if (e.key === 'ArrowLeft') {
                e.preventDefault();
                setOutputTab(tabIds[(currentIndex - 1 + tabIds.length) % tabIds.length]);
              }
            }}
            className={`flex items-center gap-2 px-4 py-2 border-b-2 transition focus:ring-2 focus:ring-gov-accent focus:ring-offset-2 focus:outline-none
              ${outputTab === id ? 'border-gov-blue text-gov-blue' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
          >
            <Icon className="w-4 h-4" aria-hidden="true" />
            {id === 'filled'
              ? t('access.filledForm')
              : t(labelKey)}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="min-h-[300px]">
        <div
          role="tabpanel"
          id="panel-form"
          aria-labelledby="tab-form"
          hidden={outputTab !== 'form'}
          tabIndex={0}
        >
          {outputTab === 'form' && (
            <div className="space-y-4">
              {Object.entries(result.formData).map(([key, data]: [string, { value: any; confidence: number }]) => (
                <div key={key} className="flex items-center gap-4 p-3 bg-gray-50 rounded-lg">
                  <div className="flex-1">
                    <span className="block text-sm font-medium text-gray-700 capitalize">
                      {key.replace(/_/g, ' ')}
                    </span>
                    <p className="text-gray-900">{String(data.value)}</p>
                  </div>
                  <div className="text-xs text-gray-500">
                    <span
                      className={`px-2 py-0.5 rounded ${data.confidence > 0.8 ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}
                      aria-label={`Confidence: ${Math.round(data.confidence * 100)}%`}
                    >
                      {Math.round(data.confidence * 100)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div
          role="tabpanel"
          id="panel-email"
          aria-labelledby="tab-email"
          hidden={outputTab !== 'email'}
          tabIndex={0}
        >
          {outputTab === 'email' && (
            <div className="relative">
              <button
                onClick={() => handleCopy(result.emailDraft)}
                className="absolute top-2 right-2 p-2 text-gray-500 hover:text-gray-700 focus:ring-2 focus:ring-gov-accent focus:ring-offset-2 focus:outline-none rounded"
                aria-label={copied ? t('access.copied') || 'Copied to clipboard' : t('access.copyEmail') || 'Copy email to clipboard'}
              >
                {copied ? <Check className="w-4 h-4 text-green-500" aria-hidden="true" /> : <Copy className="w-4 h-4" aria-hidden="true" />}
              </button>
              <pre className="whitespace-pre-wrap p-4 bg-gray-50 rounded-lg text-sm font-sans">
                {result.emailDraft || t('access.noDraft')}
              </pre>
            </div>
          )}
        </div>

        <div
          role="tabpanel"
          id="panel-meeting"
          aria-labelledby="tab-meeting"
          hidden={outputTab !== 'meeting'}
          tabIndex={0}
        >
          {outputTab === 'meeting' && (
            <div className="relative">
              <button
                onClick={() => handleCopy(result.meetingPrep)}
                className="absolute top-2 right-2 p-2 text-gray-500 hover:text-gray-700 focus:ring-2 focus:ring-gov-accent focus:ring-offset-2 focus:outline-none rounded"
                aria-label={copied ? t('access.copied') || 'Copied to clipboard' : t('access.copyMeeting') || 'Copy meeting prep to clipboard'}
              >
                {copied ? <Check className="w-4 h-4 text-green-500" aria-hidden="true" /> : <Copy className="w-4 h-4" aria-hidden="true" />}
              </button>
              <div className="p-4 bg-gray-50 rounded-lg prose prose-sm max-w-none">
                <pre className="whitespace-pre-wrap font-sans text-sm">
                  {result.meetingPrep || t('access.noPrep')}
                </pre>
              </div>
            </div>
          )}
        </div>

        {/* Filled Form Tab Panel */}
        {(filledForm || isFillingForm) && (
          <div
            role="tabpanel"
            id="panel-filled"
            aria-labelledby="tab-filled"
            hidden={outputTab !== 'filled'}
            tabIndex={0}
          >
            {outputTab === 'filled' && (
              isFillingForm ? (
                <div className="flex flex-col items-center justify-center py-12 text-gray-500">
                  <Loader2 className="w-12 h-12 mb-4 text-gov-blue animate-spin" />
                  <p className="font-medium">
                    {t('access.fillingForm')}
                  </p>
                  <p className="text-sm mt-1">
                    {t('access.matchingData')}
                  </p>
                </div>
              ) : filledForm ? (
                <FormPreview
                  filledPdfBase64={filledForm.pdfBase64}
                  fieldMapping={filledForm.fieldMapping}
                  fieldsFilled={filledForm.fieldsFilled}
                  unmappedFields={filledForm.unmappedFields}
                  unusedData={filledForm.unusedData}
                  formName={formName || 'Form'}
                  t={t}
                  language={language}
                />
              ) : null
            )}
          </div>
        )}
      </div>

      {/* Remaining Gaps Warning */}
      {result.gaps.length > 0 && (
        <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <h4 className="font-medium text-yellow-800 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            {t('access.stillMissing')}
          </h4>
          <ul className="mt-2 space-y-1">
            {result.gaps.map((gap, i) => (
              <li key={i} className="text-sm text-yellow-700">• {gap.field}: {gap.question}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
