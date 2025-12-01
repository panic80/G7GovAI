import React from 'react';
import { AlertTriangle, Truck, Activity } from 'lucide-react';
import { useLanguage } from '../../../contexts/LanguageContext';
import type { EmergencySimResponse } from '../../../services/foresightService';
import { EMERGENCY_EVENTS } from '../types';

interface EmergencyTabProps {
  eventType: string;
  emergencySim: EmergencySimResponse | null;
  onRunSim: (event: string) => void;
}

export const EmergencyTab: React.FC<EmergencyTabProps> = ({
  eventType,
  emergencySim,
  onRunSim,
}) => {
  const { t } = useLanguage();

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Event Controls */}
      <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 lg:col-span-1 h-fit">
        <h2 className="text-lg font-semibold mb-4">{t('foresight.emergencySim')}</h2>
        <div className="space-y-2">
          {EMERGENCY_EVENTS.map((event) => (
            <button
              key={event}
              onClick={() => onRunSim(event)}
              className={`w-full text-left px-4 py-3 rounded-lg border transition flex items-center justify-between ${
                eventType === event
                  ? 'border-gov-blue bg-blue-50 text-gov-blue ring-1 ring-gov-blue'
                  : 'border-gray-200 hover:bg-gray-50'
              }`}
            >
              <span>{event}</span>
              {eventType === event && <Activity className="w-4 h-4" />}
            </button>
          ))}
        </div>

        {emergencySim?.alerts.length ? (
          <div className="mt-6 p-4 bg-amber-50 border border-amber-200 rounded-lg">
            <h4 className="text-amber-800 font-bold flex items-center gap-2 mb-2">
              <AlertTriangle className="w-4 h-4" /> Alert
            </h4>
            <ul className="list-disc pl-5 text-sm text-amber-900 space-y-1">
              {emergencySim.alerts.map((alert, i) => (
                <li key={i}>{alert}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>

      {/* Map/Route Status */}
      <div className="lg:col-span-2 bg-white p-6 rounded-xl shadow-sm border border-gray-200">
        <h3 className="text-md font-bold text-gray-800 mb-4 flex items-center justify-between">
          <span>{t('foresight.networkStatus')}</span>
          <span className={`px-3 py-1 rounded-full text-xs font-bold ${
            emergencySim?.network_status === 'Critical' ? 'bg-red-100 text-red-800' :
            emergencySim?.network_status === 'High' ? 'bg-orange-100 text-orange-800' :
            'bg-green-100 text-green-800'
          }`}>
            {emergencySim?.network_status} Risk
          </span>
        </h3>

        <div className="grid gap-4">
          {emergencySim?.routes.map((route, i) => (
            <div key={i} className="flex items-center justify-between p-4 border rounded-lg bg-gray-50">
              <div className="flex items-center gap-4">
                <div className="p-2 bg-white rounded-full border">
                  <Truck className="w-5 h-5 text-gray-600" />
                </div>
                <div>
                  <div className="font-medium text-gray-900">{route.source} → {route.target}</div>
                  <div className="text-xs text-gray-500">
                    Est: {route.estimated_time} min <span className="text-gray-300">|</span> Orig: {route.original_time} min
                  </div>
                </div>
              </div>
              <div className="text-right">
                <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                   route.status === 'Blocked' ? 'bg-red-100 text-red-800' :
                   route.status === 'Delayed' ? 'bg-yellow-100 text-yellow-800' :
                   'bg-green-100 text-green-800'
                }`}>
                  {route.status}
                </span>
                {route.traffic_index > 5 && (
                  <div className="text-xs text-red-600 mt-1 font-medium">
                    Heavy Traffic (Idx: {route.traffic_index})
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-6 h-48 bg-blue-50 rounded-lg flex items-center justify-center border-2 border-dashed border-blue-200">
           <span className="text-blue-400 text-sm font-medium">Interactive Map Visualization Placeholder</span>
        </div>
      </div>
    </div>
  );
};
