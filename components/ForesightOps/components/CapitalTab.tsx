import React from 'react';
import { Sliders, Play, Activity } from 'lucide-react';
import { useLanguage } from '../../../contexts/LanguageContext';
import type { CapitalPlanResponse } from '../../../services/foresightService';

interface CapitalTabProps {
  loading: boolean;
  budget: number;
  setBudget: (value: number) => void;
  riskWeight: number;
  impactWeight: number;
  updateRiskWeight: (value: number) => void;
  updateImpactWeight: (value: number) => void;
  capitalPlan: CapitalPlanResponse | null;
  onRun: () => void;
}

export const CapitalTab: React.FC<CapitalTabProps> = ({
  loading,
  budget,
  setBudget,
  riskWeight,
  impactWeight,
  updateRiskWeight,
  updateImpactWeight,
  capitalPlan,
  onRun,
}) => {
  const { t } = useLanguage();

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
      {/* Controls */}
      <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 h-fit lg:col-span-1">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Sliders className="w-5 h-5 text-gov-blue" />
          {t('foresight.parameters')}
        </h2>

        <div className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('foresight.availableBudget')}
            </label>
            <input
              type="number"
              value={budget}
              onChange={(e) => setBudget(Number(e.target.value))}
              className="w-full p-2 border rounded focus:ring-2 focus:ring-gov-blue outline-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('foresight.riskWeight')}: {riskWeight}
            </label>
            <input
              type="range" min="0" max="1" step="0.1"
              value={riskWeight}
              onChange={(e) => updateRiskWeight(Number(e.target.value))}
              className="w-full accent-gov-blue"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('foresight.impactWeight')}: {impactWeight}
            </label>
            <input
              type="range" min="0" max="1" step="0.1"
              value={impactWeight}
              onChange={(e) => updateImpactWeight(Number(e.target.value))}
              className="w-full accent-gov-blue"
            />
          </div>

          <button
            onClick={onRun}
            disabled={loading}
            className="w-full bg-gov-blue text-white py-2 rounded hover:bg-blue-800 transition flex items-center justify-center gap-2"
          >
            {loading ? <Activity className="animate-spin w-4 h-4" /> : <Play className="w-4 h-4" />}
            {t('foresight.optimizePlan')}
          </button>
        </div>
      </div>

      {/* Results */}
      <div className="lg:col-span-3 space-y-6">
        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-blue-50 p-4 rounded-lg border border-blue-100">
            <div className="text-sm text-blue-800">{t('foresight.totalRequested')}</div>
            <div className="text-2xl font-bold text-blue-900">
              ${capitalPlan?.total_requested?.toLocaleString?.()}
            </div>
          </div>
          <div className="bg-green-50 p-4 rounded-lg border border-green-100">
            <div className="text-sm text-green-800">{t('foresight.totalFunded')}</div>
            <div className="text-2xl font-bold text-green-900">
              ${capitalPlan?.total_funded?.toLocaleString?.()}
            </div>
          </div>
          <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
            <div className="text-sm text-gray-800">{t('foresight.projectsFunded')}</div>
            <div className="text-2xl font-bold text-gray-900">
              {capitalPlan?.projects?.filter(p => p.status === 'Funded').length} / {capitalPlan?.projects?.length}
            </div>
          </div>
        </div>

        {/* Project Table */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Project</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Region</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Cond.</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Cost</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Score</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {capitalPlan?.projects?.map((project) => (
                <tr key={project.id} className={project.status === 'Funded' ? 'bg-green-50/30' : ''}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{project.name}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{project.region}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <span className={`px-2 py-1 rounded-full text-xs ${
                      project.condition_score < 50 ? 'bg-red-100 text-red-800' :
                      project.condition_score < 75 ? 'bg-yellow-100 text-yellow-800' : 'bg-green-100 text-green-800'
                    }`}>
                      {project.condition_score}/100
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${(project.replacement_cost / 1000000).toFixed(1)}M</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{project.priority_score.toFixed(2)}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                      project.status === 'Funded' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                    }`}>
                      {project.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
