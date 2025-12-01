import React from 'react';
import { FileCheck, Mail, Calendar, ArrowRight, CheckCircle2, Info, Globe } from 'lucide-react';
import { Language, G7_LANGUAGES } from '../../../contexts/LanguageContext';
import { OutputMode } from '../types';

interface ModeStepProps {
  selectedModes: OutputMode[];
  onToggleMode: (mode: OutputMode) => void;
  onContinue: () => void;
  // Language props
  language: Language;
  onLanguageChange: (lang: Language) => void;
  outputLanguage: Language;
  onOutputLanguageChange: (lang: Language) => void;
  t: (key: string) => string;
}

const MODE_CONFIG: Record<OutputMode, { icon: typeof FileCheck; titleKey: string; descKey: string }> = {
  form: {
    icon: FileCheck,
    titleKey: 'access.mode.form.title',
    descKey: 'access.mode.form.description',
  },
  email: {
    icon: Mail,
    titleKey: 'access.mode.email.title',
    descKey: 'access.mode.email.description',
  },
  meeting: {
    icon: Calendar,
    titleKey: 'access.mode.meeting.title',
    descKey: 'access.mode.meeting.description',
  },
};

export const ModeStep: React.FC<ModeStepProps> = ({
  selectedModes,
  onToggleMode,
  onContinue,
  language,
  onLanguageChange,
  outputLanguage,
  onOutputLanguageChange,
  t,
}) => {
  const canContinue = selectedModes.length > 0;
  const formSelected = selectedModes.includes('form');

  const handleKeyDown = (e: React.KeyboardEvent, mode: OutputMode) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onToggleMode(mode);
    }
  };

  const handleLanguageKeyDown = (e: React.KeyboardEvent, lang: Language) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onLanguageChange(lang);
    }
  };

  return (
    <div className="space-y-8">
      {/* Language Selection Section */}
      <div className="pb-6 border-b border-gray-200">
        <div className="text-center mb-4">
          <div className="flex items-center justify-center gap-2 mb-2">
            <Globe className="w-5 h-5 text-gov-blue" aria-hidden="true" />
            <h2 className="text-lg font-semibold text-gray-900">
              {t('access.language.select')}
            </h2>
          </div>
        </div>

        {/* G7 Language Buttons */}
        <div
          className="flex flex-wrap justify-center gap-3"
          role="radiogroup"
          aria-label={t('access.language.select')}
        >
          {G7_LANGUAGES.map((lang) => {
            const isSelected = language === lang.code;
            return (
              <button
                key={lang.code}
                role="radio"
                aria-checked={isSelected}
                onClick={() => onLanguageChange(lang.code)}
                onKeyDown={(e) => handleLanguageKeyDown(e, lang.code)}
                className={`
                  px-4 py-2 rounded-lg border-2 transition-all font-medium
                  focus:outline-none focus:ring-4 focus:ring-gov-accent focus:ring-offset-2
                  ${isSelected
                    ? 'border-gov-blue bg-gov-blue text-white shadow-md'
                    : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300 hover:bg-gray-50'
                  }
                `}
              >
                <span className="text-xs uppercase tracking-wider block">{lang.code.toUpperCase()}</span>
                <span className="text-sm">{lang.nativeName}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Mode Selection Header */}
      <div className="text-center">
        <h2 className="text-xl font-semibold text-gray-900">
          {t('access.mode.title')}
        </h2>
        <p className="mt-1 text-sm text-gray-600">
          {t('access.mode.subtitle')}
        </p>
      </div>

      {/* Mode Selection Cards */}
      <div
        className="grid grid-cols-1 md:grid-cols-3 gap-4"
        role="group"
        aria-label={t('access.mode.title')}
      >
        {(Object.keys(MODE_CONFIG) as OutputMode[]).map((mode) => {
          const config = MODE_CONFIG[mode];
          const Icon = config.icon;
          const isSelected = selectedModes.includes(mode);

          return (
            <div
              key={mode}
              role="checkbox"
              aria-checked={isSelected}
              tabIndex={0}
              onClick={() => onToggleMode(mode)}
              onKeyDown={(e) => handleKeyDown(e, mode)}
              className={`
                relative cursor-pointer rounded-xl border-2 p-6 transition-all
                focus:outline-none focus:ring-4 focus:ring-gov-accent focus:ring-offset-2
                ${isSelected
                  ? 'border-gov-blue bg-blue-50 shadow-md'
                  : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm'
                }
              `}
            >
              {/* Checkbox indicator */}
              <div
                className={`
                  absolute top-3 right-3 w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all
                  ${isSelected
                    ? 'bg-gov-blue border-gov-blue'
                    : 'border-gray-300 bg-white'
                  }
                `}
                aria-hidden="true"
              >
                {isSelected && <CheckCircle2 className="w-5 h-5 text-white" />}
              </div>

              {/* Icon */}
              <div
                className={`
                  w-12 h-12 rounded-lg flex items-center justify-center mb-4
                  ${isSelected ? 'bg-gov-blue text-white' : 'bg-gray-100 text-gray-600'}
                `}
                aria-hidden="true"
              >
                <Icon className="w-6 h-6" />
              </div>

              {/* Title */}
              <h3 className={`font-semibold mb-2 ${isSelected ? 'text-gov-blue' : 'text-gray-900'}`}>
                {t(config.titleKey)}
              </h3>

              {/* Description */}
              <p className="text-sm text-gray-600">
                {t(config.descKey)}
              </p>
            </div>
          );
        })}
      </div>

      {/* Form requires PDF notice */}
      {formSelected && (
        <div
          className="flex items-start gap-3 p-4 bg-amber-50 border border-amber-200 rounded-lg"
          role="alert"
        >
          <Info className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" aria-hidden="true" />
          <p className="text-sm text-amber-800">
            {t('access.mode.formRequired')}
          </p>
        </div>
      )}

      {/* Output Language Selection */}
      <div className="pt-6 border-t border-gray-200">
        <div className="text-center mb-4">
          <h3 className="text-lg font-semibold text-gray-900">
            {t('access.language.output')}
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            {t('access.language.outputHint')}
          </p>
        </div>

        {/* Output Language Buttons - same style as UI language */}
        <div
          className="flex flex-wrap justify-center gap-3"
          role="radiogroup"
          aria-label={t('access.language.output')}
        >
          {G7_LANGUAGES.map((lang) => {
            const isSelected = outputLanguage === lang.code;
            return (
              <button
                key={lang.code}
                role="radio"
                aria-checked={isSelected}
                onClick={() => onOutputLanguageChange(lang.code)}
                className={`
                  px-4 py-2 rounded-lg border-2 transition-all font-medium
                  focus:outline-none focus:ring-4 focus:ring-gov-accent focus:ring-offset-2
                  ${isSelected
                    ? 'border-gov-blue bg-gov-blue text-white shadow-md'
                    : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300 hover:bg-gray-50'
                  }
                `}
              >
                <span className="text-xs uppercase tracking-wider block">{lang.code.toUpperCase()}</span>
                <span className="text-sm">{lang.nativeName}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Continue Button */}
      <div className="flex justify-end pt-4">
        <button
          onClick={onContinue}
          disabled={!canContinue}
          className="flex items-center gap-2 px-6 py-3 bg-gov-blue text-white rounded-lg hover:bg-blue-800 disabled:opacity-50 disabled:cursor-not-allowed transition focus:ring-4 focus:ring-gov-accent focus:ring-offset-2 focus:outline-none"
          aria-disabled={!canContinue}
        >
          {t('btn.continue')}
          <ArrowRight className="w-4 h-4" aria-hidden="true" />
        </button>
      </div>

      {/* Validation message */}
      {!canContinue && (
        <p className="text-center text-sm text-gray-500" role="status">
          {t('access.mode.selectAtLeastOne')}
        </p>
      )}
    </div>
  );
};
