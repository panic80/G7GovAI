import React from 'react';
import { CheckCircle2 } from 'lucide-react';
import { WIZARD_STEPS, WizardStep } from '../types';

interface WizardProgressBarProps {
  currentStep: WizardStep;
  t: (key: string) => string;
}

export const WizardProgressBar: React.FC<WizardProgressBarProps> = ({ currentStep, t }) => {
  const currentIndex = WIZARD_STEPS.indexOf(currentStep);
  const progressPercent = (currentIndex / (WIZARD_STEPS.length - 1)) * 100;

  return (
    <div
      className="mb-8"
      role="navigation"
      aria-label={t('access.wizardProgress') || 'Form completion progress'}
    >
      {/* Progress Line Container */}
      <div
        className="relative flex items-center justify-between"
        role="progressbar"
        aria-valuenow={currentIndex + 1}
        aria-valuemin={1}
        aria-valuemax={WIZARD_STEPS.length}
        aria-label={`Step ${currentIndex + 1} of ${WIZARD_STEPS.length}`}
      >
        {/* Background Line */}
        <div className="absolute top-4 left-0 right-0 h-1 bg-gray-200 rounded-full mx-12"></div>
        {/* Animated Progress Line */}
        <div
          className="absolute top-4 left-0 h-1 bg-gradient-to-r from-gov-blue via-gov-accent to-gov-blue-light rounded-full transition-all duration-700 ease-out mx-12"
          style={{ width: `calc(${progressPercent}% - 96px + ${progressPercent > 0 ? '96px' : '0px'})` }}
        ></div>

        {/* Steps */}
        {WIZARD_STEPS.map((step, idx) => {
          const isActive = currentStep === step;
          const isComplete = currentIndex > idx;

          const stepLabel = step === 'mode' ? t('access.step.mode')
            : step === 'input' ? t('access.step.input')
            : step === 'processing' ? t('access.step.processing')
            : step === 'gaps' ? t('access.step.gaps')
            : t('access.step.output');

          return (
            <div
              key={step}
              className="relative z-10 flex flex-col items-center"
              role="listitem"
              aria-current={isActive ? 'step' : undefined}
            >
              {/* Step Circle */}
              <div
                className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold shadow-sm transition-all duration-300
                  ${isActive
                    ? 'bg-gradient-to-br from-gov-blue to-gov-accent text-white scale-110 animate-pulseRing'
                    : isComplete
                    ? 'bg-gradient-to-br from-green-500 to-emerald-600 text-white'
                    : 'bg-gray-100 text-gray-400 border-2 border-gray-200'
                  }`}
                aria-hidden="true"
              >
                {isComplete ? (
                  <CheckCircle2 className="w-5 h-5 animate-scaleIn" />
                ) : (
                  idx + 1
                )}
              </div>

              {/* Step Label */}
              <span
                className={`mt-2 text-xs font-medium transition-colors whitespace-nowrap ${
                  isActive
                    ? 'text-gov-blue font-semibold'
                    : isComplete
                    ? 'text-green-600'
                    : 'text-gray-400'
                }`}
              >
                {stepLabel}
                <span className="sr-only">
                  {isComplete ? ' (completed)' : isActive ? ' (current)' : ' (upcoming)'}
                </span>
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
