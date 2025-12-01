import React, { useState, useEffect, useRef } from 'react';
import { BrainCircuit, Search, BarChart3, Sparkles, CheckCircle, Circle, ChevronDown, ChevronUp } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

type StepStatus = 'pending' | 'active' | 'complete' | 'error';
type StepName = 'routing' | 'retrieving' | 'grading' | 'generating';

interface Step {
  id: StepName;
  label: string;
  icon: React.ReactNode;
}

interface GovLensProgressPanelProps {
  streamingTrace: string[];
}

// Parse trace logs to determine current step and progress
const parseProgress = (traces: string[]): { currentStep: StepName; progress: number; statusMessage: string } => {
  if (traces.length === 0) {
    return { currentStep: 'routing', progress: 5, statusMessage: 'Analyzing query...' };
  }

  const lastTrace = traces[traces.length - 1].toLowerCase();
  const allTraces = traces.join(' ').toLowerCase();

  // Check for final answer
  if (allTraces.includes('final answer') || allTraces.includes('generated')) {
    return { currentStep: 'generating', progress: 95, statusMessage: 'Generating answer...' };
  }

  // Check for grading
  if (allTraces.includes('grader') || allTraces.includes('grading') || allTraces.includes('ranking')) {
    return { currentStep: 'grading', progress: 60, statusMessage: 'Ranking documents...' };
  }

  // Check for retrieval
  if (allTraces.includes('retrieved') || allTraces.includes('retriev')) {
    // Extract document count if available
    const match = traces.join(' ').match(/retrieved (\d+)/i);
    const docCount = match ? match[1] : '';
    return {
      currentStep: 'retrieving',
      progress: 35,
      statusMessage: docCount ? `Retrieved ${docCount} documents` : 'Searching documents...'
    };
  }

  // Check for routing
  if (allTraces.includes('router') || allTraces.includes('routing') || allTraces.includes('complex') || allTraces.includes('simple')) {
    return { currentStep: 'routing', progress: 15, statusMessage: 'Determining query complexity...' };
  }

  // Default to routing
  return { currentStep: 'routing', progress: 10, statusMessage: 'Processing query...' };
};

const getStepStatus = (stepId: StepName, currentStep: StepName): StepStatus => {
  const stepOrder: StepName[] = ['routing', 'retrieving', 'grading', 'generating'];
  const currentIndex = stepOrder.indexOf(currentStep);
  const stepIndex = stepOrder.indexOf(stepId);

  if (stepIndex < currentIndex) return 'complete';
  if (stepIndex === currentIndex) return 'active';
  return 'pending';
};

export const GovLensProgressPanel: React.FC<GovLensProgressPanelProps> = ({ streamingTrace }) => {
  const { t } = useLanguage();
  const [logsExpanded, setLogsExpanded] = useState(false);
  const logsEndRef = useRef<HTMLDivElement>(null);

  const { currentStep, progress, statusMessage } = parseProgress(streamingTrace);

  const steps: Step[] = [
    { id: 'routing', label: 'Route', icon: <BrainCircuit size={16} /> },
    { id: 'retrieving', label: 'Retrieve', icon: <Search size={16} /> },
    { id: 'grading', label: 'Grade', icon: <BarChart3 size={16} /> },
    { id: 'generating', label: 'Generate', icon: <Sparkles size={16} /> },
  ];

  // Auto-scroll logs
  useEffect(() => {
    if (logsExpanded && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [streamingTrace, logsExpanded]);

  const getStepStyles = (status: StepStatus) => {
    switch (status) {
      case 'complete':
        return {
          container: 'bg-green-100 border-green-300',
          icon: 'text-green-600',
          text: 'text-green-700 font-medium',
        };
      case 'active':
        return {
          container: 'bg-blue-100 border-blue-400 animate-pulse',
          icon: 'text-gov-blue',
          text: 'text-gov-blue font-semibold',
        };
      case 'error':
        return {
          container: 'bg-red-100 border-red-300',
          icon: 'text-red-600',
          text: 'text-red-700',
        };
      default:
        return {
          container: 'bg-gray-50 border-gray-200',
          icon: 'text-gray-400',
          text: 'text-gray-400',
        };
    }
  };

  // Calculate step progress for connecting line
  const stepOrder: StepName[] = ['routing', 'retrieving', 'grading', 'generating'];
  const currentStepIndex = stepOrder.indexOf(currentStep);
  const lineProgress = ((currentStepIndex + (progress / 100)) / (stepOrder.length - 1)) * 100;

  return (
    <div className="w-full max-w-2xl bg-white rounded-xl border border-gray-200 shadow-gov overflow-hidden animate-scaleIn">
      {/* Header with gradient accent */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 px-4 py-3 border-b border-blue-100 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-gov-blue/5 to-gov-accent/5"></div>
        <div className="relative flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gov-blue/10 flex items-center justify-center">
              <BrainCircuit className="w-5 h-5 text-gov-blue animate-pulse" />
            </div>
            <span className="font-semibold text-gray-900">Processing Query</span>
          </div>
          <span className="text-sm font-bold text-gov-blue bg-white px-3 py-1 rounded-full shadow-sm border border-blue-100">
            {progress}%
          </span>
        </div>
      </div>

      <div className="p-5 space-y-5">
        {/* Animated Gradient Progress Bar */}
        <div className="w-full bg-gray-100 rounded-full h-2 overflow-hidden">
          <div
            className="h-2 rounded-full transition-all duration-500 ease-out bg-gradient-to-r from-gov-blue via-gov-accent to-gov-blue-light animate-gradientShift"
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Step Indicators with Connecting Line */}
        <div className="relative">
          {/* Connecting Line Background */}
          <div className="absolute top-5 left-[10%] right-[10%] h-0.5 bg-gray-200 rounded-full"></div>
          {/* Connecting Line Progress */}
          <div
            className="absolute top-5 left-[10%] h-0.5 bg-gradient-to-r from-green-500 to-gov-blue rounded-full transition-all duration-500"
            style={{ width: `${Math.min(lineProgress, 100) * 0.8}%` }}
          ></div>

          <div className="relative grid grid-cols-4 gap-2">
            {steps.map((step, index) => {
              const status = getStepStatus(step.id, currentStep);
              const styles = getStepStyles(status);

              return (
                <div key={step.id} className="flex flex-col items-center">
                  <div
                    className={`
                      w-10 h-10 rounded-full border-2 flex items-center justify-center
                      transition-all duration-300 ${styles.container}
                      ${status === 'active' ? 'animate-pulseRing scale-110' : ''}
                      ${status === 'complete' ? 'animate-successBounce' : ''}
                    `}
                  >
                    {status === 'complete' ? (
                      <CheckCircle size={20} className={`${styles.icon} animate-scaleIn`} />
                    ) : status === 'active' ? (
                      <div className={`${styles.icon} animate-pulse`}>{step.icon}</div>
                    ) : (
                      <Circle size={16} className={styles.icon} />
                    )}
                  </div>
                  <span className={`mt-2 text-xs ${styles.text}`}>{step.label}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Status Message with subtle animation */}
        <div className="text-center">
          <p className="text-sm text-gray-600 font-medium animate-fadeIn">{statusMessage}</p>
        </div>

        {/* Expandable Logs */}
        <div className="border-t border-gray-100 pt-3">
          <button
            onClick={() => setLogsExpanded(!logsExpanded)}
            className="flex items-center gap-2 text-xs text-gray-500 hover:text-gray-700 transition-colors"
          >
            {logsExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            <span>{logsExpanded ? 'Hide Logs' : 'View Logs'}</span>
            {streamingTrace.length > 0 && (
              <span className="bg-gray-200 text-gray-600 px-1.5 py-0.5 rounded text-[10px]">
                {streamingTrace.length}
              </span>
            )}
          </button>

          {logsExpanded && (
            <div className="mt-2 bg-slate-900 rounded-lg p-3 max-h-32 overflow-y-auto text-xs font-mono">
              {streamingTrace.length === 0 ? (
                <p className="text-gray-500 italic">Waiting for logs...</p>
              ) : (
                streamingTrace.map((trace, i) => (
                  <div key={i} className="text-gray-300 py-0.5 flex gap-2">
                    <span className="text-gray-500 select-none">[{String(i + 1).padStart(2, '0')}]</span>
                    <span className={
                      trace.toLowerCase().includes('error') ? 'text-red-400' :
                      trace.toLowerCase().includes('retrieved') || trace.toLowerCase().includes('complete') ? 'text-green-400' :
                      trace.toLowerCase().includes('warning') ? 'text-yellow-400' :
                      'text-gray-300'
                    }>
                      {trace}
                    </span>
                  </div>
                ))
              )}
              <div ref={logsEndRef} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
