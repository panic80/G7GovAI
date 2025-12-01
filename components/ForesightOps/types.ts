// ForesightOps Types

export type TabType = 'agent' | 'capital' | 'emergency';

export const CHART_COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042'] as const;

export const EMERGENCY_EVENTS = ['None', 'Snowstorm', 'Flood', 'Heatwave'] as const;
export type EmergencyEvent = typeof EMERGENCY_EVENTS[number];
