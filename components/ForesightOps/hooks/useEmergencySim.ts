import { useCallback } from 'react';
import { runEmergencySim as runSimApi, EmergencySimResponse } from '../../../services/foresightService';
import { useForesightStore } from '../../../stores/foresightStore';

export function useEmergencySim() {
  const {
    emergencyLoading: loading,
    setEmergencyLoading: setLoading,
    emergencyEventType: eventType,
    setEmergencyEventType: setEventType,
    emergencySim,
    setEmergencySim,
    addPlanningToHistory,
  } = useForesightStore();

  const runEmergencySim = useCallback(
    async (event: string) => {
      setLoading(true);
      setEventType(event);
      try {
        const result = await runSimApi(event);
        setEmergencySim(result);

        // Add to history
        addPlanningToHistory({
          type: 'emergency',
          params: {
            eventType: event,
          },
          result,
        });
      } catch (err) {
        console.error('Emergency simulation failed:', err);
      } finally {
        setLoading(false);
      }
    },
    [setLoading, setEventType, setEmergencySim, addPlanningToHistory]
  );

  return {
    loading,
    eventType,
    emergencySim,
    runEmergencySim,
  };
}
