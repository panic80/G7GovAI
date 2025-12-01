import React, { useEffect } from 'react';
import { TrendingUp, Hammer, Truck, Brain, LineChart } from 'lucide-react';
import { useLanguage } from '../../contexts/LanguageContext';
import { useForesightStream } from '../../hooks/useForesightStream';
import { useForesightStore } from '../../stores/foresightStore';

// Hooks
import { useCapitalPlanning, useEmergencySim, useForecast } from './hooks';

// Components
import { AgentTab, CapitalTab, EmergencyTab, ForecastTab } from './components';

// Types
import type { TabType } from './types';

export const ForesightOps: React.FC = () => {
  const { language, t } = useLanguage();

  // Get UI state from store
  const {
    activeTab,
    setActiveTab,
    agentBudget,
    setAgentBudget,
    agentRiskWeight,
    setAgentRiskWeight,
  } = useForesightStore();

  // AI Agent State
  const foresightStream = useForesightStream();

  // Capital Planning Hook
  const capitalPlanning = useCapitalPlanning();

  // Emergency Sim Hook
  const emergencySim = useEmergencySim();

  // Forecast Hook
  const forecast = useForecast();

  // Handlers
  const handleRunAgent = async () => {
    await foresightStream.optimize({
      budgetTotal: agentBudget,
      weights: { risk: agentRiskWeight, coverage: 1 - agentRiskWeight },
      language,
    });
  };

  // Initial Load - only run if no data exists
  useEffect(() => {
    if (!capitalPlanning.capitalPlan) {
      capitalPlanning.runCapitalPlan();
    }
    if (!emergencySim.emergencySim) {
      emergencySim.runEmergencySim('None');
    }
  }, []);

  return (
    <div className="max-w-7xl mx-auto p-6">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
          <TrendingUp className="w-8 h-8 text-gov-blue" />
          {t('nav.foresight')}
          <span className="text-lg font-normal text-gray-500">| {t('nav.foresight.desc')}</span>
        </h1>
        <p className="text-gray-600 mt-2">
          {t('foresight.subtitle')}
        </p>
      </header>

      {/* Tabs */}
      <div className="flex space-x-4 mb-6 border-b border-gray-200">
        <button
          onClick={() => setActiveTab('agent')}
          className={`pb-2 px-4 font-medium text-sm flex items-center gap-2 ${
            activeTab === 'agent'
              ? 'border-b-2 border-gov-blue text-gov-blue'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <Brain className="w-4 h-4" />
          {t('foresight.tab.agent')}
          <span className="px-1.5 py-0.5 text-xs bg-blue-100 text-blue-700 rounded-full">{t('foresight.new')}</span>
        </button>
        <button
          onClick={() => setActiveTab('capital')}
          className={`pb-2 px-4 font-medium text-sm flex items-center gap-2 ${
            activeTab === 'capital'
              ? 'border-b-2 border-gov-blue text-gov-blue'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <Hammer className="w-4 h-4" />
          {t('foresight.tab.capital')}
        </button>
        <button
          onClick={() => setActiveTab('emergency')}
          className={`pb-2 px-4 font-medium text-sm flex items-center gap-2 ${
            activeTab === 'emergency'
              ? 'border-b-2 border-gov-blue text-gov-blue'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <Truck className="w-4 h-4" />
          {t('foresight.tab.emergency')}
        </button>
        <button
          onClick={() => setActiveTab('forecast')}
          className={`pb-2 px-4 font-medium text-sm flex items-center gap-2 ${
            activeTab === 'forecast'
              ? 'border-b-2 border-gov-blue text-gov-blue'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <LineChart className="w-4 h-4" />
          Forecast
          <span className="px-1.5 py-0.5 text-xs bg-purple-100 text-purple-700 rounded-full">New</span>
        </button>
      </div>

      {/* AI Agent Tab */}
      {activeTab === 'agent' && (
        <AgentTab
          agentBudget={agentBudget}
          setAgentBudget={setAgentBudget}
          agentRiskWeight={agentRiskWeight}
          setAgentRiskWeight={setAgentRiskWeight}
          foresightStream={foresightStream}
          onRunAgent={handleRunAgent}
        />
      )}

      {/* Capital Tab */}
      {activeTab === 'capital' && (
        <CapitalTab
          loading={capitalPlanning.loading}
          budget={capitalPlanning.budget}
          setBudget={capitalPlanning.setBudget}
          riskWeight={capitalPlanning.riskWeight}
          impactWeight={capitalPlanning.impactWeight}
          updateRiskWeight={capitalPlanning.updateRiskWeight}
          updateImpactWeight={capitalPlanning.updateImpactWeight}
          capitalPlan={capitalPlanning.capitalPlan}
          onRun={capitalPlanning.runCapitalPlan}
        />
      )}

      {/* Emergency Tab */}
      {activeTab === 'emergency' && (
        <EmergencyTab
          eventType={emergencySim.eventType}
          emergencySim={emergencySim.emergencySim}
          onRunSim={emergencySim.runEmergencySim}
        />
      )}

      {/* Forecast Tab */}
      {activeTab === 'forecast' && (
        <ForecastTab
          loading={forecast.loading}
          onRunForecast={forecast.runForecast}
          conditionForecasts={forecast.conditionForecasts}
          demandForecasts={forecast.demandForecasts}
          riskTimeline={forecast.riskTimeline}
          externalFactors={forecast.externalFactors}
          bottlenecks={forecast.bottlenecks}
          horizonYears={forecast.horizonYears}
          setHorizonYears={forecast.setHorizonYears}
        />
      )}
    </div>
  );
};

export default ForesightOps;
