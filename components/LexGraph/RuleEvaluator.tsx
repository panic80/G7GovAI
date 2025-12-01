import React, { useState } from 'react';
import { Check, X, History, Calendar, RotateCcw, GitBranch, List, Scale } from 'lucide-react';
import { RulesResponse, TraceStep, StepData, DecisionTreeNode, LegislationMap, LegislativeExcerpt } from '../../types';
import { useLanguage } from '../../contexts/LanguageContext';
import { StepProgress } from './StepProgress';
import { DecisionSummary } from './DecisionSummary';
import { DecisionTreeView } from './DecisionTreeView';
import { LegislationMapPanel } from './LegislationMapPanel';
import { LegislativeExcerptModal } from './LegislativeExcerptModal';

interface RuleEvaluatorProps {
  scenario: string;
  setScenario: (s: string) => void;
  evalDate: string;
  setEvalDate: (d: string) => void;
  loading: boolean;
  stepData: StepData;
  result: RulesResponse | null;
  error: string | null;
  onEvaluate: () => void;
  onReset: () => void;
  // Legislative source integration props
  decisionTree?: DecisionTreeNode | null;
  legislationMap?: LegislationMap | null;
  viewMode?: 'trace' | 'tree';
  onViewModeChange?: (mode: 'trace' | 'tree') => void;
}

export const RuleEvaluator: React.FC<RuleEvaluatorProps> = ({
  scenario,
  setScenario,
  evalDate,
  setEvalDate,
  loading,
  stepData,
  result,
  error,
  onEvaluate,
  onReset,
  decisionTree,
  legislationMap,
  viewMode: externalViewMode,
  onViewModeChange,
}) => {
  const { language, t } = useLanguage();
  const [internalViewMode, setInternalViewMode] = useState<'trace' | 'tree'>('trace');
  const [selectedExcerpt, setSelectedExcerpt] = useState<LegislativeExcerpt | null>(null);
  const [showLegislationMap, setShowLegislationMap] = useState(false);

  // Use external view mode if provided, otherwise use internal state
  const viewMode = externalViewMode ?? internalViewMode;
  const handleViewModeChange = (mode: 'trace' | 'tree') => {
    if (onViewModeChange) {
      onViewModeChange(mode);
    } else {
      setInternalViewMode(mode);
    }
  };

  const presetScenarios = language === 'fr' ? [
    "Infirmière autorisée avec offre d'emploi à temps plein au Canada, salaire de 85 000$ par année, CLB 7 en anglais, baccalauréat en sciences infirmières.",
    "Ingénieur logiciel avec 3 ans d'expérience, offre d'emploi au Royaume-Uni payant £45,000 par année, maîtrise en informatique.",
    "Travailleur de la construction avec offre d'emploi saisonnière de 6 mois, salaire de 25$ l'heure, pas de diplôme postsecondaire.",
    "Médecin avec offre d'emploi permanente, salaire de 200 000$, mais employeur détenu à 60% par le demandeur."
  ] : [
    "Registered nurse with full-time job offer in Canada, salary $85,000 per year, CLB 7 in English, Bachelor's degree in Nursing.",
    "Software engineer with 3 years experience, job offer in UK paying £45,000 per year, Master's degree in Computer Science.",
    "Construction worker with seasonal 6-month job offer, wage $25/hour, no post-secondary education.",
    "Physician with permanent job offer, salary $200,000, but employer is 60% owned by the applicant."
  ];

  // Check if any step has started
  const hasStarted = stepData.retrieve.status !== 'pending';

  const renderTraceSteps = (trace: TraceStep[] | undefined) => {
    if (!trace || trace.length === 0) {
      return (
        <div className="flex items-center justify-center h-32 text-gray-400 border-2 border-dashed border-gray-300 rounded-lg">
          {t('lexgraph.noTrace')}
        </div>
      );
    }

    return (
      <div className="space-y-0 relative">
        <div className="absolute left-4 top-4 bottom-4 w-0.5 bg-gray-300"></div>

        {trace.map((step, idx) => (
          <div key={idx} className="relative pl-12 pb-6">
            <div className="absolute left-0 top-1 w-8 h-8 bg-white border-2 border-gov-blue rounded-full flex items-center justify-center z-10 font-bold text-xs text-gov-blue">
              {idx + 1}
            </div>
            <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200 hover:border-gov-blue transition">
              <div className="flex justify-between items-start mb-2">
                <h4 className="font-bold text-gray-800 text-sm">{step.clause}</h4>
                <div className="flex items-center text-xs text-gray-500 gap-1 bg-gray-100 px-2 py-0.5 rounded">
                  <History size={12} />
                  {step.version}
                </div>
              </div>
              <p className="text-sm text-gray-600">{step.reason}</p>
              {step.source_id && (
                <div className="mt-2 pt-2 border-t border-gray-100">
                  <span className="text-xs text-gov-blue font-medium bg-blue-50 px-2 py-1 rounded">
                    {t('lexgraph.ref')} {step.source_id}
                  </span>
                </div>
              )}
            </div>
          </div>
        ))}

        {result && result.decision && (
          <div className="relative pl-12">
            <div className={`absolute left-0 top-1 w-8 h-8 rounded-full flex items-center justify-center z-10 text-white
                ${result.decision.eligible ? 'bg-green-600' : 'bg-red-600'}`}>
              {result.decision.eligible ? <Check size={16} /> : <X size={16} />}
            </div>
            <div className="pt-2">
                <span className="font-bold text-gray-900">{t('lexgraph.finalDecision')}</span>
                <p className="text-sm text-gray-500">{t('lexgraph.effectiveDate')} {result.decision.effective_date}</p>
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-8 flex-grow overflow-hidden h-full">
        {/* Left Panel - Input */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 flex flex-col h-full overflow-y-auto">
        <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold">{t('label.scenario')}</h2>
            <div className="flex items-center gap-2 bg-gray-50 px-3 py-1 rounded-lg border border-gray-200">
            <Calendar size={16} className="text-gov-blue" />
            <input
                type="date"
                value={evalDate}
                onChange={(e) => setEvalDate(e.target.value)}
                className="bg-transparent text-sm font-medium text-gray-700 outline-none"
            />
            </div>
        </div>

        <textarea
            value={scenario}
            onChange={(e) => setScenario(e.target.value)}
            className="w-full h-32 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-gov-blue outline-none resize-none"
            placeholder={t('lexgraph.placeholder')}
        />

        <div className="mt-4 space-y-2">
            <p className="text-xs text-gray-500 uppercase font-bold">{t('lexgraph.examples')}</p>
            {presetScenarios.map((s, i) => (
            <button
                key={i}
                onClick={() => setScenario(s)}
                className="block text-sm text-gov-blue hover:underline text-left"
            >
                {s}
            </button>
            ))}
        </div>

        <div className="mt-6 flex justify-end gap-2">
            {hasStarted && (
              <button
                onClick={onReset}
                className="px-4 py-2.5 rounded-md border border-gray-300 text-gray-600 hover:bg-gray-50 transition flex items-center gap-2"
              >
                <RotateCcw size={16} />
                {t('btn.reset')}
              </button>
            )}
            <button
              onClick={onEvaluate}
              disabled={loading || !scenario.trim()}
              className="bg-gov-blue text-white px-6 py-2.5 rounded-md hover:bg-blue-800 transition disabled:opacity-50"
            >
              {loading ? t('btn.tracing') : t('btn.evaluate')}
            </button>
        </div>
        </div>

        {/* Right Panel - Progress + Results */}
        <div className="bg-gray-50 p-6 rounded-xl border border-gray-200 h-full overflow-y-auto">
        {/* Header with view toggle */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">
            {loading ? t('lexgraph.progress') : t('lexgraph.decisionTrace')}
          </h2>

          <div className="flex items-center gap-2">
            {/* View Mode Toggle */}
            {!loading && result && decisionTree && (
              <div className="flex bg-white rounded-lg border border-gray-200 p-0.5">
                <button
                  onClick={() => handleViewModeChange('trace')}
                  className={`px-3 py-1.5 text-xs font-medium rounded-md flex items-center gap-1.5 transition-colors ${
                    viewMode === 'trace'
                      ? 'bg-gov-blue text-white'
                      : 'text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  <List size={14} />
                  Trace
                </button>
                <button
                  onClick={() => handleViewModeChange('tree')}
                  className={`px-3 py-1.5 text-xs font-medium rounded-md flex items-center gap-1.5 transition-colors ${
                    viewMode === 'tree'
                      ? 'bg-gov-blue text-white'
                      : 'text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  <GitBranch size={14} />
                  Tree
                </button>
              </div>
            )}

            {/* Legislation Map Toggle */}
            {!loading && legislationMap && (
              <button
                onClick={() => setShowLegislationMap(!showLegislationMap)}
                className={`px-3 py-1.5 text-xs font-medium rounded-lg flex items-center gap-1.5 border transition-colors ${
                  showLegislationMap
                    ? 'bg-blue-50 border-blue-200 text-blue-700'
                    : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'
                }`}
              >
                <Scale size={14} />
                Legislation
              </button>
            )}

            {/* Decision Badge */}
            {!loading && result && (
               <>
                {result.trace?.some(tr => tr.clause === 'Validation' || tr.clause === 'Confidence Check') ? (
                     <span className="px-3 py-1 text-sm rounded-full font-bold flex items-center gap-2 bg-yellow-100 text-yellow-700">
                        <History size={16} />
                        {t('lexgraph.insufficientData')}
                    </span>
                ) : result.decision ? (
                    <span className={`px-3 py-1 text-sm rounded-full font-bold flex items-center gap-2
                        ${result.decision.eligible ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                        {result.decision.eligible ? <Check size={16} /> : <X size={16} />}
                        {result.decision.eligible ? t('lexgraph.eligible') : t('lexgraph.ineligible')}
                    </span>
                ) : null}
               </>
            )}
          </div>
        </div>

        {/* Show StepProgress while loading or if started but no final result yet */}
        {(loading || (hasStarted && !result)) && (
          <div className="mb-6">
            <StepProgress stepData={stepData} language={language} />
          </div>
        )}

        {/* Show error if any */}
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-800">
            <strong>{t('lexgraph.error')}</strong>
            <p>{error}</p>
          </div>
        )}

        {/* Show validation warning */}
        {result?.trace?.find(tr => tr.clause === 'Validation') && (
            <div className="mb-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-800">
                <strong>{t('lexgraph.missingInfo')}</strong>
                <p>{result.trace?.find(tr => tr.clause === 'Validation')?.reason}</p>
            </div>
        )}

        {/* Legislation Map Panel (shown when toggled) */}
        {showLegislationMap && legislationMap && (
          <div className="mb-6">
            <LegislationMapPanel
              legislationMap={legislationMap}
              onExcerptClick={setSelectedExcerpt}
            />
          </div>
        )}

        {/* Show final results when complete */}
        {!loading && result ? (
          <>
            {/* Decision Summary with explanation */}
            {result.decision && (
              <div className="mb-6">
                <DecisionSummary
                  decision={result.decision}
                  explanation={result.explanation}
                  trace={result.trace || []}
                  language={language}
                />
              </div>
            )}

            {/* View Mode: Tree or Trace */}
            {viewMode === 'tree' && decisionTree ? (
              <DecisionTreeView
                tree={decisionTree}
                onExcerptClick={setSelectedExcerpt}
              />
            ) : (
              /* Detailed trace steps */
              renderTraceSteps(result.trace)
            )}
          </>
        ) : !hasStarted ? (
          <div className="flex items-center justify-center h-64 text-gray-400 border-2 border-dashed border-gray-300 rounded-lg">
            {t('lexgraph.awaiting')}
          </div>
        ) : null}
        </div>

        {/* Legislative Excerpt Modal */}
        <LegislativeExcerptModal
          excerpt={selectedExcerpt}
          onClose={() => setSelectedExcerpt(null)}
        />
    </div>
  );
};
