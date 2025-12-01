import React, { useState } from 'react';
import { Check, X, ChevronDown, ChevronUp, MessageSquare, ListChecks } from 'lucide-react';
import { DecisionResult, TraceStep } from '../../types';

interface DecisionSummaryProps {
  decision: DecisionResult;
  explanation?: string;
  trace: TraceStep[];
  language?: string;
}

export const DecisionSummary: React.FC<DecisionSummaryProps> = ({
  decision,
  explanation,
  trace,
  language = 'en',
}) => {
  const [showConditions, setShowConditions] = useState(false);
  const isFr = language === 'fr';

  // Parse trace steps to determine pass/fail status
  const conditions = trace
    .filter((t) => t.clause !== 'Additional Info Needed' && t.source_id !== 'System')
    .map((t) => {
      const passed = t.reason.toLowerCase().includes('pass');
      const failed = t.reason.toLowerCase().includes('fail');
      return {
        clause: t.clause,
        reason: t.reason,
        passed: passed && !failed,
        confidence: t.confidence,
      };
    });

  const passedCount = conditions.filter((c) => c.passed).length;
  const failedCount = conditions.filter((c) => !c.passed).length;

  return (
    <div
      className={`rounded-xl border-2 overflow-hidden shadow-gov-lg animate-resultReveal ${
        decision.eligible
          ? 'bg-green-50 border-green-500'
          : 'bg-red-50 border-red-500'
      }`}
    >
      {/* Header with Dramatic Reveal */}
      <div
        className={`px-6 py-5 flex items-center gap-4 ${
          decision.eligible
            ? 'bg-gradient-to-r from-green-100 via-green-50 to-emerald-100'
            : 'bg-gradient-to-r from-red-100 via-red-50 to-rose-100'
        }`}
      >
        {/* Large Animated Icon */}
        <div
          className={`w-14 h-14 rounded-full flex items-center justify-center shadow-lg animate-successBounce ${
            decision.eligible
              ? 'bg-gradient-to-br from-green-500 to-emerald-600'
              : 'bg-gradient-to-br from-red-500 to-rose-600'
          }`}
        >
          {decision.eligible ? (
            <Check className="text-white animate-scaleIn" size={32} />
          ) : (
            <X className="text-white animate-scaleIn" size={32} />
          )}
        </div>
        <div className="flex-grow">
          <h3
            className={`font-extrabold text-2xl tracking-tight ${
              decision.eligible ? 'text-green-800' : 'text-red-800'
            }`}
          >
            {decision.eligible
              ? isFr
                ? 'ADMISSIBLE'
                : 'ELIGIBLE'
              : isFr
              ? 'NON ADMISSIBLE'
              : 'INELIGIBLE'}
          </h3>
          <p className="text-sm text-gray-600 mt-1">
            {isFr ? 'Date effective:' : 'Effective Date:'}{' '}
            <span className="font-medium">{decision.effective_date}</span>
          </p>
        </div>
        {/* Confidence Badge */}
        <div
          className={`px-3 py-1.5 rounded-full text-xs font-bold ${
            decision.eligible
              ? 'bg-green-200 text-green-800'
              : 'bg-red-200 text-red-800'
          }`}
        >
          {decision.confidence || 'HIGH'}
        </div>
      </div>

      {/* Explanation */}
      {explanation && (
        <div className="px-4 py-3 border-b border-gray-200">
          <div className="flex items-start gap-2">
            <MessageSquare
              size={16}
              className={`mt-0.5 flex-shrink-0 ${
                decision.eligible ? 'text-green-600' : 'text-red-600'
              }`}
            />
            <p className="text-sm text-gray-700 leading-relaxed">{explanation}</p>
          </div>
        </div>
      )}

      {/* Conditions Summary */}
      <div className="px-4 py-2">
        <button
          onClick={() => setShowConditions(!showConditions)}
          className="w-full flex items-center justify-between py-2 text-sm text-gray-600 hover:text-gray-800 transition"
        >
          <div className="flex items-center gap-2">
            <ListChecks size={16} />
            <span>
              {isFr ? 'Conditions' : 'Conditions'}: {passedCount}{' '}
              {isFr ? 'reussies' : 'passed'}, {failedCount}{' '}
              {isFr ? 'echouees' : 'failed'}
            </span>
          </div>
          {showConditions ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>

        {/* Expandable Conditions List with Staggered Animation */}
        {showConditions && (
          <div className="mt-2 space-y-2 pb-3 stagger-children">
            {conditions.map((condition, idx) => (
              <div
                key={idx}
                className={`flex items-start gap-3 p-3 rounded-lg text-sm border transition-all hover:scale-[1.01] ${
                  condition.passed
                    ? 'bg-green-50 border-green-200 hover:border-green-300'
                    : 'bg-red-50 border-red-200 hover:border-red-300'
                }`}
              >
                <div
                  className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 ${
                    condition.passed ? 'bg-green-500' : 'bg-red-500'
                  }`}
                >
                  {condition.passed ? (
                    <Check size={14} className="text-white" />
                  ) : (
                    <X size={14} className="text-white" />
                  )}
                </div>
                <div className="flex-grow min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span
                      className={`font-semibold ${
                        condition.passed ? 'text-green-800' : 'text-red-800'
                      }`}
                    >
                      {condition.clause}
                    </span>
                    {condition.confidence && (
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                          condition.confidence === 'HIGH'
                            ? 'bg-green-200 text-green-700'
                            : condition.confidence === 'MEDIUM'
                            ? 'bg-yellow-200 text-yellow-700'
                            : 'bg-red-200 text-red-700'
                        }`}
                      >
                        {condition.confidence}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-gray-500 mt-1 line-clamp-2">{condition.reason}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
