import { CONFIG } from "../config";
import { logInteraction } from "./auditService";

export interface Project {
  id: string;
  name: string;
  type: string;
  region: string;
  age_years: number;
  condition_score: number;
  daily_usage: number;
  replacement_cost: number;
  population_growth_rate: number;
  predicted_failure_prob: number;
  failure_impact: number;
  priority_score: number;
  status: 'Funded' | 'Deferred';
}

export interface CapitalPlanResponse {
  total_requested: number;
  total_funded: number;
  projects: Project[];
}

export interface RouteStatus {
  source: string;
  target: string;
  original_time: number;
  estimated_time: number;
  status: 'Blocked' | 'Delayed' | 'On Time';
  traffic_index: number;
}

export interface EmergencySimResponse {
  event: string;
  network_status: string;
  routes: RouteStatus[];
  alerts: string[];
}

export const getCapitalPlan = async (
  budget: number, 
  riskWeight: number, 
  impactWeight: number
): Promise<CapitalPlanResponse> => {
  const start = Date.now();
  try {
    const response = await fetch(`${CONFIG.RAG.BASE_URL}/foresight/capital-plan`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        budget: budget,
        priorities: { risk: riskWeight, impact: impactWeight }
      })
    });

    if (!response.ok) throw new Error(`Capital Plan Failed: ${response.statusText}`);
    
    const data = await response.json();
    logInteraction('ForesightOps', 'Capital Plan Generated', Date.now() - start, 'success');
    return data;
  } catch (error) {
    logInteraction('ForesightOps', 'Capital Plan Failed', Date.now() - start, 'error', { error: String(error) });
    throw error;
  }
};

export const runEmergencySim = async (eventType: string): Promise<EmergencySimResponse> => {
  const start = Date.now();
  try {
    const response = await fetch(`${CONFIG.RAG.BASE_URL}/foresight/emergency-sim`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        event_type: eventType
      })
    });

    if (!response.ok) throw new Error(`Emergency Sim Failed: ${response.statusText}`);

    const data = await response.json();
    logInteraction('ForesightOps', 'Emergency Sim Run', Date.now() - start, 'success', { event: eventType });
    return data;
  } catch (error) {
    logInteraction('ForesightOps', 'Emergency Sim Failed', Date.now() - start, 'error', { error: String(error) });
    throw error;
  }
};
