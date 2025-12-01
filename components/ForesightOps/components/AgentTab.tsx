import React, { useState } from 'react';
import { Brain, Sparkles, Loader2, ChevronDown, ChevronUp } from 'lucide-react';
import { useLanguage } from '../../../contexts/LanguageContext';
import { StepCard } from '../../ui/StepCard';
import { RISK_THRESHOLDS } from '../../../constants';
import type { UseForesightStreamReturn } from '../../../hooks/useForesightStream';
import type { ForesightAllocation } from '../../../types';

interface AgentTabProps {
  agentBudget: number;
  setAgentBudget: (value: number) => void;
  agentRiskWeight: number;
  setAgentRiskWeight: (value: number) => void;
  foresightStream: UseForesightStreamReturn;
  onRunAgent: () => void;
}

export const AgentTab: React.FC<AgentTabProps> = ({
  agentBudget,
  setAgentBudget,
  agentRiskWeight,
  setAgentRiskWeight,
  foresightStream,
  onRunAgent,
}) => {
  const { t } = useLanguage();
  const [showTrace, setShowTrace] = useState(false);

  const {
    stepData: agentStepData,
    traceLog,
    loading: agentLoading,
    result: agentResult,
    error: agentError,
    reset: resetAgent,
  } = foresightStream;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Controls Panel */}
      <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 h-fit">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-gov-blue" />
          {t('foresight.params')}
        </h2>

        <div className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('foresight.budget')}
            </label>
            <input
              type="number"
              value={agentBudget}
              onChange={(e) => setAgentBudget(Number(e.target.value))}
              className="w-full p-2 border rounded focus:ring-2 focus:ring-gov-blue outline-none"
            />
            <p className="text-xs text-gray-500 mt-1">${(agentBudget / 1_000_000).toFixed(1)}{t('foresight.million')}</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('foresight.riskPriority')}: {(agentRiskWeight * 100).toFixed(0)}%
            </label>
            <input
              type="range" min="0" max="1" step="0.1"
              value={agentRiskWeight}
              onChange={(e) => setAgentRiskWeight(Number(e.target.value))}
              className="w-full accent-gov-blue"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>{t('foresight.coverage')}</span>
              <span>{t('foresight.risk')}</span>
            </div>
          </div>

          <button
            onClick={onRunAgent}
            disabled={agentLoading}
            className="w-full bg-gradient-to-r from-gov-blue to-gov-accent text-white py-3.5 rounded-xl hover:shadow-gov-lg transition-all duration-300 flex items-center justify-center gap-2 font-semibold transform hover:-translate-y-0.5 disabled:opacity-70 disabled:transform-none"
          >
            {agentLoading ? (
              <>
                <Loader2 className="animate-spin w-5 h-5" />
                {t('foresight.optimizing')}
              </>
            ) : (
              <>
                <Brain className="w-5 h-5" />
                {t('foresight.runOptimization')}
              </>
            )}
          </button>

          {agentResult && (
            <button
              onClick={resetAgent}
              className="w-full text-gray-600 py-2 rounded border border-gray-200 hover:bg-gray-50 transition text-sm"
            >
              {t('btn.reset')}
            </button>
          )}
        </div>

        {/* Progress Steps */}
        <div className="mt-6 space-y-3">
          <h3 className="text-sm font-medium text-gray-700 mb-3">
            {t('foresight.agentSteps')}
          </h3>
          <StepCard
            title={t('foresight.step.parse')}
            status={agentStepData.parse_request.status}
          />
          <StepCard
            title={t('foresight.step.retrieve')}
            status={agentStepData.retrieve_assets.status}
            stats={agentStepData.retrieve_assets.status === 'completed' ? [
              { label: 'Assets', value: agentStepData.retrieve_assets.assetCount }
            ] : undefined}
          />
          <StepCard
            title={t('foresight.step.calculate')}
            status={agentStepData.calculate_risks.status}
            stats={agentStepData.calculate_risks.status === 'completed' ? [
              { label: 'Critical', value: agentStepData.calculate_risks.riskDistribution.critical || 0 },
              { label: 'High', value: agentStepData.calculate_risks.riskDistribution.high || 0 },
            ] : undefined}
          />
          <StepCard
            title={t('foresight.step.optimize')}
            status={agentStepData.optimize_allocation.status}
            stats={agentStepData.optimize_allocation.status === 'completed' ? [
              { label: 'Funded', value: agentStepData.optimize_allocation.assetsFunded },
              { label: 'Budget Used', value: `$${(agentStepData.optimize_allocation.totalAllocated / 1_000_000).toFixed(1)}M` },
            ] : undefined}
          />
          <StepCard
            title={t('foresight.step.synthesize')}
            status={agentStepData.synthesize.status}
            stats={agentStepData.synthesize.status === 'completed' ? [
              { label: 'Confidence', value: `${(agentStepData.synthesize.confidence * 100).toFixed(0)}%` }
            ] : undefined}
          />
        </div>
      </div>

      {/* Results Panel */}
      <div className="lg:col-span-2 space-y-6">
        {agentError && (
          <div className="bg-red-50 border border-red-200 text-red-800 p-4 rounded-lg">
            <strong>Error:</strong> {agentError}
          </div>
        )}

        {agentResult && (
          <>
            {/* Summary Cards with Staggered Animation */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 stagger-children">
              <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-5 rounded-xl border border-blue-200 shadow-sm transform hover:scale-105 hover:shadow-gov transition-all duration-300">
                <div className="text-sm text-blue-800 font-medium">{t('foresight.totalBudget')}</div>
                <div className="text-3xl font-bold text-blue-900 mt-1">${(agentBudget / 1_000_000).toFixed(1)}M</div>
              </div>
              <div className="bg-gradient-to-br from-green-50 to-emerald-100 p-5 rounded-xl border border-green-200 shadow-sm transform hover:scale-105 hover:shadow-gov transition-all duration-300">
                <div className="text-sm text-green-800 font-medium">{t('foresight.allocated')}</div>
                <div className="text-3xl font-bold text-green-900 mt-1">${(agentResult.totalAllocated / 1_000_000).toFixed(1)}M</div>
              </div>
              <div className="bg-gradient-to-br from-purple-50 to-violet-100 p-5 rounded-xl border border-purple-200 shadow-sm transform hover:scale-105 hover:shadow-gov transition-all duration-300">
                <div className="text-sm text-purple-800 font-medium">{t('foresight.funded')}</div>
                <div className="text-3xl font-bold text-purple-900 mt-1">{agentResult.assetsFunded}</div>
              </div>
              <div className="bg-gradient-to-br from-amber-50 to-orange-100 p-5 rounded-xl border border-amber-200 shadow-sm transform hover:scale-105 hover:shadow-gov transition-all duration-300">
                <div className="text-sm text-amber-800 font-medium">{t('foresight.riskAddressed')}</div>
                <div className="text-3xl font-bold text-amber-900 mt-1">{agentResult.riskReductionPct.toFixed(0)}%</div>
              </div>
            </div>

            {/* AI Recommendations */}
            <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-gov-blue" />
                {t('foresight.recommendations')}
              </h3>
              <div className="prose prose-sm max-w-none text-gray-700 whitespace-pre-wrap">
                {agentResult.recommendations}
              </div>
            </div>

            {/* Allocation Table */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
              <div className="p-4 border-b border-gray-200 flex items-center justify-between">
                <h3 className="font-semibold">{t('foresight.detailedAllocations')}</h3>
                <span className="text-sm text-gray-500">{agentResult.allocations.length} assets</span>
              </div>
              <div className="overflow-x-auto max-h-96 overflow-y-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50 sticky top-0">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">#</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Asset</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Region</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Cond.</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Risk</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Cost</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {agentResult.allocations.map((alloc: ForesightAllocation) => (
                      <tr key={alloc.asset_id} className={alloc.status === 'Funded' ? 'bg-green-50/50' : ''}>
                        <td className="px-4 py-3 text-sm text-gray-500">{alloc.rank}</td>
                        <td className="px-4 py-3 text-sm font-medium text-gray-900">{alloc.asset_name}</td>
                        <td className="px-4 py-3 text-sm text-gray-500">{alloc.region}</td>
                        <td className="px-4 py-3 text-sm">
                          <span className={`px-2 py-1 rounded-full text-xs ${
                            alloc.current_condition < 30 ? 'bg-red-100 text-red-800' :
                            alloc.current_condition < 60 ? 'bg-yellow-100 text-yellow-800' :
                            'bg-green-100 text-green-800'
                          }`}>
                            {alloc.current_condition.toFixed(0)}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <span className={`px-2 py-1 rounded-full text-xs ${
                            alloc.risk_score >= RISK_THRESHOLDS.HIGH ? 'bg-red-100 text-red-800' :
                            alloc.risk_score >= RISK_THRESHOLDS.MEDIUM ? 'bg-orange-100 text-orange-800' :
                            alloc.risk_score >= 0.2 ? 'bg-yellow-100 text-yellow-800' :
                            'bg-green-100 text-green-800'
                          }`}>
                            {(alloc.risk_score * 100).toFixed(0)}%
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-500">
                          ${(alloc.replacement_cost / 1_000_000).toFixed(1)}M
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                            alloc.status === 'Funded' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'
                          }`}>
                            {alloc.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Trace Log (collapsible) */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
              <button
                onClick={() => setShowTrace(!showTrace)}
                className="w-full p-4 flex items-center justify-between text-left hover:bg-gray-50"
              >
                <span className="font-medium">{t('foresight.traceLog')}</span>
                {showTrace ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>
              {showTrace && (
                <div className="p-4 border-t border-gray-200 bg-gray-50">
                  <ul className="space-y-1 text-sm font-mono text-gray-600">
                    {traceLog.map((log, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <span className="text-gray-400">{i + 1}.</span>
                        <span>{log}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </>
        )}

        {!agentResult && !agentLoading && (
          <div className="bg-gradient-to-br from-gray-50 to-blue-50/30 border-2 border-dashed border-gray-200 rounded-2xl p-12 text-center animate-fadeIn">
            <div className="w-20 h-20 rounded-2xl bg-gov-blue/10 flex items-center justify-center mx-auto mb-6 animate-float">
              <Brain className="w-10 h-10 text-gov-blue" />
            </div>
            <h3 className="text-xl font-semibold text-gray-700 mb-2">
              {t('foresight.readyToOptimize')}
            </h3>
            <p className="text-gray-500 max-w-md mx-auto leading-relaxed">
              {t('foresight.readyDescription')}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
