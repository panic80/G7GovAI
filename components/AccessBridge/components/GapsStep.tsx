import React, { useState } from 'react';
import { AlertTriangle, Volume2, StopCircle, Loader2, ArrowLeft, ArrowRight, ChevronDown, Check } from 'lucide-react';
import type { InformationGap } from '../../../types';

interface GapsStepProps {
  gaps: InformationGap[];
  followUpAnswers: Record<string, string>;
  setFollowUpAnswers: React.Dispatch<React.SetStateAction<Record<string, string>>>;
  speaking: boolean;
  audioLoading: boolean;
  onSpeakGaps: () => void;
  onBack: () => void;
  onSubmit: () => void;
  t: (key: string) => string;
}

export const GapsStep: React.FC<GapsStepProps> = ({
  gaps,
  followUpAnswers,
  setFollowUpAnswers,
  speaking,
  audioLoading,
  onSpeakGaps,
  onBack,
  onSubmit,
  t,
}) => {
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);

  // Helper to handle checkbox multi-select
  const handleCheckboxChange = (field: string, option: string, checked: boolean) => {
    const currentValue = followUpAnswers[field] || '';
    const currentOptions = currentValue ? currentValue.split(',').filter(Boolean) : [];

    let newOptions: string[];
    if (checked) {
      newOptions = [...currentOptions, option];
    } else {
      newOptions = currentOptions.filter((o) => o !== option);
    }

    setFollowUpAnswers((prev) => ({ ...prev, [field]: newOptions.join(',') }));
  };

  // Check if an option is selected for checkbox
  const isCheckboxSelected = (field: string, option: string): boolean => {
    const currentValue = followUpAnswers[field] || '';
    const currentOptions = currentValue ? currentValue.split(',').filter(Boolean) : [];
    return currentOptions.includes(option);
  };

  return (
    <div className="space-y-6" role="form" aria-labelledby="gaps-heading">
      <div className="flex items-center justify-between">
        <h2 id="gaps-heading" className="text-xl font-semibold flex items-center gap-2">
          <AlertTriangle className="w-6 h-6 text-yellow-500" aria-hidden="true" />
          {t('access.missingInfo')}
        </h2>
        <button
          onClick={onSpeakGaps}
          disabled={audioLoading}
          className="flex items-center gap-2 px-3 py-1.5 text-sm bg-yellow-100 text-yellow-700 rounded-lg hover:bg-yellow-200 focus:ring-2 focus:ring-yellow-500 focus:ring-offset-2 focus:outline-none"
          aria-label={speaking ? t('btn.stopListening') || 'Stop listening' : t('btn.listen')}
          aria-pressed={speaking}
        >
          {audioLoading ? <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" /> : speaking ? <StopCircle className="w-4 h-4" aria-hidden="true" /> : <Volume2 className="w-4 h-4" aria-hidden="true" />}
          {t('btn.listen')}
        </button>
      </div>

      <p className="text-gray-600" id="gaps-description">
        {t('access.missingDescription')}
      </p>

      <div className="space-y-4" role="list" aria-describedby="gaps-description">
        {gaps.map((gap, idx) => (
          <div key={idx} className="p-4 bg-gray-50 rounded-lg border border-gray-200" role="listitem">
            <div className="block text-sm font-medium text-gray-700 mb-1">
              {gap.question}
              {gap.priority === 'critical' && (
                <span className="ml-2 text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded" aria-label="Required field">
                  {t('label.required')}
                </span>
              )}
            </div>
            <p id={`gap-help-${gap.field}`} className="text-xs text-gray-500 mb-3">{gap.why_needed}</p>

            {/* Text Input (default) */}
            {(!gap.input_type || gap.input_type === 'text') && (
              <input
                id={`gap-field-${gap.field}`}
                type="text"
                value={followUpAnswers[gap.field] || ''}
                onChange={(e) => setFollowUpAnswers((prev) => ({ ...prev, [gap.field]: e.target.value }))}
                className="w-full p-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-gov-blue focus:border-gov-blue focus:outline-none"
                placeholder={t('access.enterAnswer')}
                aria-describedby={`gap-help-${gap.field}`}
                aria-required={gap.priority === 'critical'}
              />
            )}

            {/* Radio Buttons (single select) */}
            {gap.input_type === 'radio' && gap.options && (
              <div role="radiogroup" aria-labelledby={`gap-field-${gap.field}`} className="space-y-2">
                {gap.options.map((option) => (
                  <label
                    key={option}
                    className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition ${
                      followUpAnswers[gap.field] === option
                        ? 'border-gov-blue bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300 hover:bg-gray-100'
                    }`}
                  >
                    <input
                      type="radio"
                      name={`gap-radio-${gap.field}`}
                      value={option}
                      checked={followUpAnswers[gap.field] === option}
                      onChange={(e) => setFollowUpAnswers((prev) => ({ ...prev, [gap.field]: e.target.value }))}
                      className="w-4 h-4 text-gov-blue focus:ring-gov-blue"
                    />
                    <span className="text-sm text-gray-700">{option}</span>
                  </label>
                ))}
              </div>
            )}

            {/* Checkboxes (multi-select) */}
            {gap.input_type === 'checkbox' && gap.options && (
              <div role="group" aria-labelledby={`gap-field-${gap.field}`} className="space-y-2">
                {gap.options.map((option) => (
                  <label
                    key={option}
                    className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition ${
                      isCheckboxSelected(gap.field, option)
                        ? 'border-gov-blue bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300 hover:bg-gray-100'
                    }`}
                  >
                    <div
                      className={`w-5 h-5 rounded border flex items-center justify-center ${
                        isCheckboxSelected(gap.field, option)
                          ? 'bg-gov-blue border-gov-blue'
                          : 'border-gray-300'
                      }`}
                    >
                      {isCheckboxSelected(gap.field, option) && (
                        <Check className="w-3 h-3 text-white" />
                      )}
                    </div>
                    <input
                      type="checkbox"
                      checked={isCheckboxSelected(gap.field, option)}
                      onChange={(e) => handleCheckboxChange(gap.field, option, e.target.checked)}
                      className="sr-only"
                    />
                    <span className="text-sm text-gray-700">{option}</span>
                  </label>
                ))}
              </div>
            )}

            {/* Styled Dropdown (single select with custom UI) */}
            {gap.input_type === 'dropdown' && gap.options && (
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setOpenDropdown(openDropdown === gap.field ? null : gap.field)}
                  className="w-full p-2.5 border border-gray-300 rounded-lg flex justify-between items-center bg-white hover:border-gray-400 focus:ring-2 focus:ring-gov-blue focus:border-gov-blue focus:outline-none"
                  aria-haspopup="listbox"
                  aria-expanded={openDropdown === gap.field}
                >
                  <span className={followUpAnswers[gap.field] ? 'text-gray-900' : 'text-gray-400'}>
                    {followUpAnswers[gap.field] || t('access.selectOption') || 'Select an option...'}
                  </span>
                  <ChevronDown className={`w-4 h-4 text-gray-500 transition ${openDropdown === gap.field ? 'rotate-180' : ''}`} />
                </button>
                {openDropdown === gap.field && (
                  <div
                    className="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-y-auto"
                    role="listbox"
                  >
                    {gap.options.map((option) => (
                      <button
                        key={option}
                        type="button"
                        role="option"
                        aria-selected={followUpAnswers[gap.field] === option}
                        onClick={() => {
                          setFollowUpAnswers((prev) => ({ ...prev, [gap.field]: option }));
                          setOpenDropdown(null);
                        }}
                        className={`w-full px-4 py-2.5 text-left text-sm hover:bg-gray-100 transition flex items-center justify-between ${
                          followUpAnswers[gap.field] === option ? 'bg-blue-50 text-gov-blue' : 'text-gray-700'
                        }`}
                      >
                        {option}
                        {followUpAnswers[gap.field] === option && (
                          <Check className="w-4 h-4 text-gov-blue" />
                        )}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="flex justify-between">
        <button
          onClick={onBack}
          className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:text-gray-900 focus:ring-2 focus:ring-gov-accent focus:ring-offset-2 focus:outline-none rounded-lg"
        >
          <ArrowLeft className="w-4 h-4" aria-hidden="true" />
          {t('btn.back')}
        </button>
        <button
          onClick={onSubmit}
          className="flex items-center gap-2 px-6 py-3 bg-gov-blue text-white rounded-lg hover:bg-blue-800 transition focus:ring-4 focus:ring-gov-accent focus:ring-offset-2 focus:outline-none"
        >
          {t('btn.continue')}
          <ArrowRight className="w-4 h-4" aria-hidden="true" />
        </button>
      </div>
    </div>
  );
};
