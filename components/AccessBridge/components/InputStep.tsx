import React from 'react';
import { Type, Upload, Mic, CheckCircle2, Sparkles, ArrowRight, ArrowLeft, FileText } from 'lucide-react';
import { Language } from '../../../contexts/LanguageContext';
import { VoiceRecorder } from '../../VoiceRecorder';
import { FileUploader } from '../../FileUploader';
import { FormUpload } from './FormUpload';
import type { OutputMode } from '../types';

interface FormField {
  name: string;
  type: string;
  label: string;
  options?: string[];
  required: boolean;
}

interface FormTemplate {
  pdfBase64: string;
  formName: string;
  fields: FormField[];
}

interface InputStepProps {
  textInput: string;
  setTextInput: (value: string) => void;
  documentTexts: string[];
  audioTranscripts: string[];
  onFilesProcessed: (texts: string[]) => void;
  onVoiceTranscript: (text: string) => void;
  onProcess: () => void;
  canProcess: boolean;
  formTemplate: FormTemplate | null;
  onFormUploaded: (formData: FormTemplate) => void;
  onFormClear: () => void;
  selectedModes: OutputMode[];
  onBack: () => void;
  language: Language;
  t: (key: string) => string;
}

export const InputStep: React.FC<InputStepProps> = ({
  textInput,
  setTextInput,
  documentTexts,
  audioTranscripts,
  onFilesProcessed,
  onVoiceTranscript,
  onProcess,
  canProcess,
  formTemplate,
  onFormUploaded,
  onFormClear,
  selectedModes,
  onBack,
  language,
  t,
}) => {
  const formRequired = selectedModes.includes('form');

  return (
    <div className="space-y-6">
      {/* All Three Input Modes - Stacked */}
      <div className="space-y-6">
        {/* 1. Text Input Section */}
        <div className="border border-gray-200 rounded-lg overflow-hidden">
          <div className="bg-gray-50 px-4 py-2 border-b border-gray-200 flex items-center gap-2">
            <Type className="w-4 h-4 text-gov-blue" aria-hidden="true" />
            <label htmlFor="accessbridge-text-input" className="font-medium text-gray-700">
              {t('access.textInput')}
            </label>
            {textInput.trim() && (
              <span className="ml-auto text-xs text-green-600 flex items-center gap-1" aria-live="polite">
                <CheckCircle2 className="w-3 h-3" aria-hidden="true" />
                {textInput.length} {t('access.chars')}
              </span>
            )}
          </div>
          <textarea
            id="accessbridge-text-input"
            value={textInput}
            onChange={(e) => setTextInput(e.target.value)}
            className="w-full h-32 p-4 border-0 focus:ring-2 focus:ring-gov-accent focus:ring-inset font-mono text-sm resize-none"
            placeholder={t('access.textPlaceholder')}
            aria-describedby="text-input-help"
          />
          <span id="text-input-help" className="sr-only">
            {t('access.textPlaceholder')}
          </span>
        </div>

        {/* 2. Document Upload Section */}
        <fieldset className="border border-gray-200 rounded-lg overflow-hidden">
          <legend className="sr-only">{t('access.documentUpload')}</legend>
          <div className="bg-gray-50 px-4 py-2 border-b border-gray-200 flex items-center gap-2">
            <Upload className="w-4 h-4 text-gov-blue" aria-hidden="true" />
            <span className="font-medium text-gray-700">
              {t('access.documentUpload')}
            </span>
            {documentTexts.length > 0 && (
              <span className="ml-auto text-xs text-green-600 flex items-center gap-1" aria-live="polite">
                <CheckCircle2 className="w-3 h-3" aria-hidden="true" />
                {documentTexts.length} {t('access.files')}
              </span>
            )}
          </div>
          <div className="p-4">
            <FileUploader onFilesProcessed={onFilesProcessed} />
          </div>
        </fieldset>

        {/* 3. Voice Input Section */}
        <fieldset className="border border-gray-200 rounded-lg overflow-hidden">
          <legend className="sr-only">{t('access.voiceRecording')}</legend>
          <div className="bg-gray-50 px-4 py-2 border-b border-gray-200 flex items-center gap-2">
            <Mic className="w-4 h-4 text-gov-blue" aria-hidden="true" />
            <span className="font-medium text-gray-700">
              {t('access.voiceRecording')}
            </span>
            {audioTranscripts.length > 0 && (
              <span className="ml-auto text-xs text-green-600 flex items-center gap-1" aria-live="polite">
                <CheckCircle2 className="w-3 h-3" aria-hidden="true" />
                {audioTranscripts.length} {t('access.recordings')}
              </span>
            )}
          </div>
          <div className="p-4">
            <div className="flex flex-col items-center justify-center py-4">
              <VoiceRecorder onTranscript={onVoiceTranscript} />
            </div>
            {audioTranscripts.length > 0 && (
              <div className="mt-4 border-t pt-4" role="region" aria-label={t('access.transcriptions')}>
                <h4 className="text-sm font-medium text-gray-700 mb-2">
                  {t('access.transcriptions')}
                </h4>
                <ul className="space-y-2 max-h-32 overflow-y-auto" aria-label={t('access.transcriptions')}>
                  {audioTranscripts.map((transcript, i) => (
                    <li key={i} className="p-2 bg-gray-50 rounded border text-sm">
                      <span className="text-gray-500 text-xs mr-2" aria-hidden="true">#{i + 1}</span>
                      <span className="sr-only">Recording {i + 1}: </span>
                      {transcript.substring(0, 150)}{transcript.length > 150 ? '...' : ''}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </fieldset>

        {/* 4. Form Template Upload Section - Only show when "Fill out a form" mode is selected */}
        {formRequired && (
          <fieldset className={`border rounded-lg overflow-hidden ${
            !formTemplate
              ? 'border-red-300 bg-red-50/30'
              : 'border-gray-200'
          }`}>
            <legend className="sr-only">
              {language === 'fr' ? 'Télécharger un formulaire PDF' : 'Upload PDF Form'}
            </legend>
            <div className={`px-4 py-2 border-b flex items-center gap-2 ${
              !formTemplate
                ? 'bg-red-50 border-red-200'
                : 'bg-gray-50 border-gray-200'
            }`}>
              <FileText className="w-4 h-4 text-gov-blue" aria-hidden="true" />
              <span className="font-medium text-gray-700">
                {language === 'fr' ? 'Formulaire PDF à remplir' : 'PDF Form to Fill'}
                <span className="ml-2 text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded">
                  {t('label.required')}
                </span>
              </span>
              {formTemplate && (
                <span className="ml-auto text-xs text-green-600 flex items-center gap-1" aria-live="polite">
                  <CheckCircle2 className="w-3 h-3" aria-hidden="true" />
                  {formTemplate.fields.length} {language === 'fr' ? 'champs' : 'fields'}
                </span>
              )}
            </div>
            <div className="p-4">
              <FormUpload
                onFormUploaded={onFormUploaded}
                onClear={onFormClear}
                uploadedForm={formTemplate}
                language={language}
                t={t}
              />
            </div>
          </fieldset>
        )}
      </div>

      {/* Navigation Buttons */}
      <div className="flex justify-between">
        <button
          onClick={onBack}
          className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition focus:ring-2 focus:ring-gov-accent focus:ring-offset-2 focus:outline-none"
        >
          <ArrowLeft className="w-4 h-4" aria-hidden="true" />
          {t('btn.back')}
        </button>

        <button
          onClick={onProcess}
          disabled={!canProcess}
          className="flex items-center gap-2 px-6 py-3 bg-gov-blue text-white rounded-lg hover:bg-blue-800 disabled:opacity-50 disabled:cursor-not-allowed transition focus:ring-4 focus:ring-gov-accent focus:ring-offset-2 focus:outline-none"
          aria-disabled={!canProcess}
        >
          <Sparkles className="w-5 h-5" aria-hidden="true" />
          {t('access.processExtract')}
          <ArrowRight className="w-4 h-4" aria-hidden="true" />
        </button>
      </div>
    </div>
  );
};
