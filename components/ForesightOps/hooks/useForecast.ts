import { useCallback } from 'react';
import { useForesightStore } from '../../../stores/foresightStore';
import { streamWithCallback } from '../../../services/apiClient';

export function useForecast() {
  const {
    forecastLoading: loading,
    setForecastLoading: setLoading,
    forecastHorizonYears: horizonYears,
    setForecastHorizonYears: setHorizonYears,
    conditionForecasts,
    setConditionForecasts,
    demandForecasts,
    setDemandForecasts,
    riskTimeline,
    setRiskTimeline,
    externalFactors,
    setExternalFactors,
    bottlenecks,
    setBottlenecks,
    resetForecast,
    agentBudget,
    agentRiskWeight,
  } = useForesightStore();

  const runForecast = useCallback(async () => {
    setLoading(true);
    resetForecast();

    try {
      // Use the existing foresight stream endpoint which now includes forecast data
      await streamWithCallback<{ node: string; state: Record<string, any> }>(
        '/agent/foresight/stream',
        {
          query: `Run anticipatory forecast for ${horizonYears} year planning horizon`,
          language: 'en',
          budget_total: agentBudget,
          planning_horizon_years: horizonYears,
          weights: { risk: agentRiskWeight, coverage: 1 - agentRiskWeight },
          include_scenarios: false,
        },
        (event) => {
          const nodeName = event.node;
          const eventState = event.state || {};

          // Handle forecast node output
          if (nodeName === 'forecast') {
            if (eventState.condition_forecasts) {
              setConditionForecasts(eventState.condition_forecasts);
            }
            if (eventState.demand_forecasts) {
              setDemandForecasts(eventState.demand_forecasts);
            }
            if (eventState.risk_timeline) {
              setRiskTimeline(eventState.risk_timeline);
            }
            if (eventState.external_factors) {
              setExternalFactors(eventState.external_factors);
            }
            if (eventState.bottlenecks) {
              setBottlenecks(eventState.bottlenecks);
            }
          }

          // Handle error node
          if (nodeName === 'error') {
            console.error('Forecast error:', eventState.error);
          }
        }
      );
    } catch (error) {
      console.error('Forecast failed:', error);
    } finally {
      setLoading(false);
    }
  }, [
    horizonYears,
    agentBudget,
    agentRiskWeight,
    setLoading,
    resetForecast,
    setConditionForecasts,
    setDemandForecasts,
    setRiskTimeline,
    setExternalFactors,
    setBottlenecks,
  ]);

  return {
    loading,
    horizonYears,
    setHorizonYears,
    conditionForecasts,
    demandForecasts,
    riskTimeline,
    externalFactors,
    bottlenecks,
    runForecast,
    resetForecast,
  };
}
