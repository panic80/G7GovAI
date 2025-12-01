import { useCallback } from 'react';
import { getCapitalPlan, CapitalPlanResponse } from '../../../services/foresightService';
import { useForesightStore } from '../../../stores/foresightStore';

export function useCapitalPlanning() {
  const {
    capitalLoading: loading,
    setCapitalLoading: setLoading,
    capitalBudget: budget,
    setCapitalBudget: setBudget,
    capitalRiskWeight: riskWeight,
    capitalImpactWeight: impactWeight,
    updateCapitalWeights,
    capitalPlan,
    setCapitalPlan,
    addPlanningToHistory,
  } = useForesightStore();

  const runCapitalPlan = useCallback(async () => {
    setLoading(true);
    try {
      const result = await getCapitalPlan(budget, riskWeight, impactWeight);
      setCapitalPlan(result);

      // Add to history
      addPlanningToHistory({
        type: 'capital',
        params: {
          budget,
          riskWeight,
          impactWeight,
        },
        result,
      });
    } catch (err) {
      console.error('Capital planning failed:', err);
    } finally {
      setLoading(false);
    }
  }, [budget, riskWeight, impactWeight, setLoading, setCapitalPlan, addPlanningToHistory]);

  const updateRiskWeight = useCallback(
    (value: number) => {
      updateCapitalWeights(value);
    },
    [updateCapitalWeights]
  );

  const updateImpactWeight = useCallback(
    (value: number) => {
      updateCapitalWeights(parseFloat((1 - value).toFixed(1)));
    },
    [updateCapitalWeights]
  );

  return {
    loading,
    budget,
    setBudget,
    riskWeight,
    impactWeight,
    updateRiskWeight,
    updateImpactWeight,
    capitalPlan,
    runCapitalPlan,
  };
}
