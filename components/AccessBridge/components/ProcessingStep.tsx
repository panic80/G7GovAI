import React from 'react';
import { BrainCircuit } from 'lucide-react';
import { StepCard } from '../../ui/StepCard';
import type { StepStatus } from '../../../types';

interface StepData {
  process_input: { status: StepStatus; filesProcessed?: number };
  retrieve_program: { status: StepStatus; requiredFields?: string[] };
  extract_info: { status: StepStatus; fieldsExtracted?: number };
  analyze_gaps: { status: StepStatus; gapsFound?: number; criticalGaps?: number };
  generate_outputs: { status: StepStatus; outputsReady?: string[] };
}

interface ProcessingStepProps {
  stepData: StepData;
  traceLog: string[];
  error: string | null;
  t: (key: string) => string;
}

export const ProcessingStep: React.FC<ProcessingStepProps> = ({
  stepData,
  traceLog,
  error,
  t,
}) => {

  // Determine current processing step for screen reader announcement
  const getCurrentStepName = () => {
    if (stepData.generate_outputs.status === 'in_progress') return t('access.step.generateOutputs');
    if (stepData.analyze_gaps.status === 'in_progress') return t('access.step.analyzeGaps');
    if (stepData.extract_info.status === 'in_progress') return t('access.step.extractInfo');
    if (stepData.retrieve_program.status === 'in_progress') return t('access.step.programContext');
    if (stepData.process_input.status === 'in_progress') return t('access.step.processInput');
    return t('access.processing');
  };

  return (
    <div className="space-y-6" role="region" aria-labelledby="processing-heading" aria-busy="true">
      <h2 id="processing-heading" className="text-xl font-semibold flex items-center gap-2">
        <BrainCircuit className="w-6 h-6 text-gov-blue" aria-hidden="true" />
        {t('access.processing')}
      </h2>

      {/* Screen reader live region for status updates */}
      <div aria-live="polite" aria-atomic="true" className="sr-only">
        {t('access.currentlyProcessing') || 'Currently processing'}: {getCurrentStepName()}
      </div>

      {/* Step Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4" role="list" aria-label={t('access.processingSteps') || 'Processing steps'}>
        <StepCard
          title={t('access.step.processInput')}
          status={stepData.process_input.status}
          stats={stepData.process_input.filesProcessed ? [{ label: 'Files', value: stepData.process_input.filesProcessed }] : undefined}
        />
        <StepCard
          title={t('access.step.programContext')}
          status={stepData.retrieve_program.status}
          stats={stepData.retrieve_program.requiredFields ? [{ label: 'Fields', value: stepData.retrieve_program.requiredFields.length }] : undefined}
        />
        <StepCard
          title={t('access.step.extractInfo')}
          status={stepData.extract_info.status}
          stats={stepData.extract_info.fieldsExtracted ? [{ label: 'Extracted', value: stepData.extract_info.fieldsExtracted }] : undefined}
        />
        <StepCard
          title={t('access.step.analyzeGaps')}
          status={stepData.analyze_gaps.status}
          stats={stepData.analyze_gaps.gapsFound !== undefined ? [
            { label: 'Gaps', value: stepData.analyze_gaps.gapsFound },
            { label: 'Critical', value: stepData.analyze_gaps.criticalGaps || 0 },
          ] : undefined}
        />
        <StepCard
          title={t('access.step.generateOutputs')}
          status={stepData.generate_outputs.status}
          stats={stepData.generate_outputs.outputsReady ? [{ label: 'Ready', value: stepData.generate_outputs.outputsReady.join(', ') }] : undefined}
        />
      </div>

      {/* Trace Log */}
      {traceLog.length > 0 && (
        <div className="bg-gray-50 rounded-lg p-4" role="log" aria-label={t('access.processingLog')}>
          <h4 className="text-sm font-medium text-gray-700 mb-2">
            {t('access.processingLog')}
          </h4>
          <div className="space-y-1 max-h-32 overflow-y-auto" aria-live="polite">
            {traceLog.map((log, i) => (
              <p key={i} className="text-xs text-gray-600 flex items-start gap-2">
                <BrainCircuit className="w-3 h-3 mt-0.5 flex-shrink-0 text-gov-blue" aria-hidden="true" />
                {log}
              </p>
            ))}
          </div>
        </div>
      )}

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700" role="alert">
          {error}
        </div>
      )}
    </div>
  );
};
