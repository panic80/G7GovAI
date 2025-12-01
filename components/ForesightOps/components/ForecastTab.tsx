import React, { useState, useEffect } from 'react';
import {
  TrendingDown,
  Calendar,
  AlertTriangle,
  Cloud,
  Users,
  Activity,
  Loader2,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Target,
} from 'lucide-react';
import { useLanguage } from '../../../contexts/LanguageContext';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  AreaChart,
  Area,
} from 'recharts';

// Forecast types - using permissive typing for complex backend data
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type ForecastData = Record<string, any>;

interface ForecastTabProps {
  loading: boolean;
  onRunForecast: () => void;
  conditionForecasts: ForecastData[];
  demandForecasts: ForecastData[];
  riskTimeline: ForecastData[] | null;
  externalFactors: ForecastData | null;
  bottlenecks: ForecastData[];
  horizonYears: number;
  setHorizonYears: (years: number) => void;
}

export const ForecastTab: React.FC<ForecastTabProps> = ({
  loading,
  onRunForecast,
  conditionForecasts,
  demandForecasts,
  riskTimeline,
  externalFactors,
  bottlenecks,
  horizonYears,
  setHorizonYears,
}) => {
  const { t } = useLanguage();
  const [selectedAsset, setSelectedAsset] = useState<string | null>(null);
  const [showExternalFactors, setShowExternalFactors] = useState(false);

  // Select first asset by default when forecasts load
  useEffect(() => {
    if (conditionForecasts.length > 0 && !selectedAsset) {
      setSelectedAsset(conditionForecasts[0].asset_id);
    }
  }, [conditionForecasts, selectedAsset]);

  // Get selected asset's forecast data
  const selectedConditionForecast = conditionForecasts.find(
    (f) => f.asset_id === selectedAsset
  );
  const selectedDemandForecast = demandForecasts.find(
    (f) => f.asset_id === selectedAsset
  );

  // Count critical assets
  const criticalAssets = conditionForecasts.filter(
    (f) => f.years_to_failure && f.years_to_failure <= 3
  );
  const expansionNeeded = demandForecasts.filter((f) => f.requires_expansion);

  // Format chart data for condition forecast
  const conditionChartData = selectedConditionForecast?.forecast_points?.map(
    (point: ForecastData) => ({
      year: point.year,
      condition: point.condition,
      failureProb: Math.round((point.failure_prob ?? 0) * 100),
    })
  ) || [];

  // Format chart data for demand forecast
  const demandChartData = selectedDemandForecast?.forecast_points?.map(
    (point: ForecastData) => ({
      year: point.year,
      demand: point.demand,
      capacity: point.capacity,
      utilization: Math.round((point.capacity_utilization ?? 0) * 100),
    })
  ) || [];

  return (
    <div className="space-y-6">
      {/* Controls Bar */}
      <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-200 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Calendar className="w-5 h-5 text-gray-500" />
            <span className="text-sm font-medium text-gray-700">Forecast Horizon:</span>
            <select
              value={horizonYears}
              onChange={(e) => setHorizonYears(Number(e.target.value))}
              className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-gov-blue outline-none"
            >
              <option value={3}>3 Years</option>
              <option value={5}>5 Years</option>
              <option value={10}>10 Years</option>
            </select>
          </div>
        </div>

        <button
          onClick={onRunForecast}
          disabled={loading}
          className="bg-gradient-to-r from-gov-blue to-gov-accent text-white px-6 py-2.5 rounded-lg hover:shadow-lg transition-all duration-300 flex items-center gap-2 font-medium disabled:opacity-70"
        >
          {loading ? (
            <>
              <Loader2 className="animate-spin w-4 h-4" />
              Forecasting...
            </>
          ) : (
            <>
              <RefreshCw className="w-4 h-4" />
              Run Forecast
            </>
          )}
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-5 rounded-xl border border-blue-200 shadow-sm">
          <div className="flex items-center gap-2 text-blue-800">
            <Activity className="w-4 h-4" />
            <span className="text-sm font-medium">Assets Forecasted</span>
          </div>
          <div className="text-3xl font-bold text-blue-900 mt-2">
            {conditionForecasts.length}
          </div>
        </div>

        <div className="bg-gradient-to-br from-red-50 to-red-100 p-5 rounded-xl border border-red-200 shadow-sm">
          <div className="flex items-center gap-2 text-red-800">
            <AlertTriangle className="w-4 h-4" />
            <span className="text-sm font-medium">Critical (3yr)</span>
          </div>
          <div className="text-3xl font-bold text-red-900 mt-2">
            {criticalAssets.length}
          </div>
          <div className="text-xs text-red-700 mt-1">Expected to fail within 3 years</div>
        </div>

        <div className="bg-gradient-to-br from-amber-50 to-amber-100 p-5 rounded-xl border border-amber-200 shadow-sm">
          <div className="flex items-center gap-2 text-amber-800">
            <TrendingDown className="w-4 h-4" />
            <span className="text-sm font-medium">Expansion Needed</span>
          </div>
          <div className="text-3xl font-bold text-amber-900 mt-2">
            {expansionNeeded.length}
          </div>
          <div className="text-xs text-amber-700 mt-1">Capacity expansion required</div>
        </div>

        <div className="bg-gradient-to-br from-green-50 to-green-100 p-5 rounded-xl border border-green-200 shadow-sm">
          <div className="flex items-center gap-2 text-green-800">
            <Target className="w-4 h-4" />
            <span className="text-sm font-medium">Bottlenecks</span>
          </div>
          <div className="text-3xl font-bold text-green-900 mt-2">
            {bottlenecks.length}
          </div>
          <div className="text-xs text-green-700 mt-1">Infrastructure constraints identified</div>
        </div>
      </div>

      {/* External Factors Panel */}
      {externalFactors && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <button
            onClick={() => setShowExternalFactors(!showExternalFactors)}
            className="w-full p-4 flex items-center justify-between text-left hover:bg-gray-50"
          >
            <div className="flex items-center gap-3">
              <Cloud className="w-5 h-5 text-gov-blue" />
              <span className="font-semibold">External Factors Impact</span>
              {externalFactors.weather && (
                <span className={`px-2 py-0.5 text-xs rounded-full ${
                  externalFactors.weather.risk_level === 'Critical' ? 'bg-red-100 text-red-800' :
                  externalFactors.weather.risk_level === 'High' ? 'bg-orange-100 text-orange-800' :
                  externalFactors.weather.risk_level === 'Medium' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-green-100 text-green-800'
                }`}>
                  Weather: {externalFactors.weather.risk_level}
                </span>
              )}
            </div>
            {showExternalFactors ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>

          {showExternalFactors && (
            <div className="p-4 border-t border-gray-200 grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Weather Impact */}
              {externalFactors.weather && (
                <div className="space-y-3">
                  <h4 className="font-medium flex items-center gap-2">
                    <Cloud className="w-4 h-4 text-blue-500" />
                    Weather Risk ({externalFactors.weather.region})
                  </h4>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="bg-blue-50 p-2 rounded">
                      <span className="text-gray-600">Flood Risk:</span>
                      <span className="font-medium ml-2">{(externalFactors.weather.flood_risk * 100).toFixed(0)}%</span>
                    </div>
                    <div className="bg-cyan-50 p-2 rounded">
                      <span className="text-gray-600">Snowstorm:</span>
                      <span className="font-medium ml-2">{(externalFactors.weather.snowstorm_risk * 100).toFixed(0)}%</span>
                    </div>
                    <div className="bg-orange-50 p-2 rounded">
                      <span className="text-gray-600">Heatwave:</span>
                      <span className="font-medium ml-2">{(externalFactors.weather.heatwave_risk * 100).toFixed(0)}%</span>
                    </div>
                    <div className="bg-purple-50 p-2 rounded">
                      <span className="text-gray-600">Impact Factor:</span>
                      <span className="font-medium ml-2">{externalFactors.weather.impact_factor.toFixed(2)}x</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Demographics Impact */}
              {externalFactors.demographics && (
                <div className="space-y-3">
                  <h4 className="font-medium flex items-center gap-2">
                    <Users className="w-4 h-4 text-green-500" />
                    Demographics ({externalFactors.demographics.region})
                  </h4>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="bg-green-50 p-2 rounded">
                      <span className="text-gray-600">Density:</span>
                      <span className="font-medium ml-2">{externalFactors.demographics.population_density.toLocaleString()}/km²</span>
                    </div>
                    <div className="bg-teal-50 p-2 rounded">
                      <span className="text-gray-600">Median Age:</span>
                      <span className="font-medium ml-2">{externalFactors.demographics.median_age}</span>
                    </div>
                    <div className="bg-emerald-50 p-2 rounded col-span-2">
                      <span className="text-gray-600">Demand Index:</span>
                      <span className="font-medium ml-2">{(externalFactors.demographics.demand_index * 100).toFixed(0)}%</span>
                      <div className="w-full bg-gray-200 rounded-full h-2 mt-1">
                        <div
                          className="bg-green-500 h-2 rounded-full"
                          style={{ width: `${externalFactors.demographics.demand_index * 100}%` }}
                        />
                      </div>
                    </div>
                  </div>
                  {externalFactors.demographics.growth_drivers && (
                    <div className="text-xs text-gray-600">
                      <span className="font-medium">Growth Drivers:</span> {externalFactors.demographics.growth_drivers.join(', ')}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Asset Selector & Details */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Activity className="w-5 h-5 text-gov-blue" />
            Asset Forecasts
          </h3>

          <div className="space-y-2 max-h-80 overflow-y-auto">
            {conditionForecasts.map((forecast) => (
              <button
                key={forecast.asset_id}
                onClick={() => setSelectedAsset(forecast.asset_id)}
                className={`w-full text-left p-3 rounded-lg border transition ${
                  selectedAsset === forecast.asset_id
                    ? 'border-gov-blue bg-blue-50'
                    : 'border-gray-200 hover:bg-gray-50'
                }`}
              >
                <div className="flex justify-between items-start">
                  <div>
                    <div className="font-medium text-sm">{forecast.asset_id}</div>
                    <div className="text-xs text-gray-500">{forecast.asset_type}</div>
                  </div>
                  <div className="text-right">
                    <div className={`text-sm font-medium ${
                      forecast.current_condition < 40 ? 'text-red-600' :
                      forecast.current_condition < 60 ? 'text-amber-600' :
                      'text-green-600'
                    }`}>
                      {forecast.current_condition}/100
                    </div>
                    {forecast.years_to_failure && (
                      <div className="text-xs text-red-500">
                        Fails in {forecast.years_to_failure}yr
                      </div>
                    )}
                  </div>
                </div>
                <div className="mt-2 flex gap-2">
                  <span className="text-xs bg-gray-100 px-2 py-0.5 rounded">
                    -{forecast.deterioration_rate}/yr
                  </span>
                </div>
              </button>
            ))}
          </div>

          {conditionForecasts.length === 0 && !loading && (
            <div className="text-center py-8 text-gray-500">
              <Activity className="w-12 h-12 mx-auto mb-2 opacity-30" />
              <p className="text-sm">Run forecast to see predictions</p>
            </div>
          )}
        </div>

        {/* Charts */}
        <div className="lg:col-span-2 space-y-6">
          {/* Condition Forecast Chart */}
          {selectedConditionForecast && conditionChartData.length > 0 && (
            <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
              <h3 className="text-lg font-semibold mb-4">
                Condition Forecast: {selectedConditionForecast.asset_id}
              </h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={conditionChartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="year" />
                    <YAxis yAxisId="left" domain={[0, 100]} />
                    <YAxis yAxisId="right" orientation="right" domain={[0, 100]} />
                    <Tooltip />
                    <Legend />
                    <Area
                      yAxisId="left"
                      type="monotone"
                      dataKey="condition"
                      name="Condition Score"
                      stroke="#2563eb"
                      fill="#3b82f6"
                      fillOpacity={0.3}
                    />
                    <Line
                      yAxisId="right"
                      type="monotone"
                      dataKey="failureProb"
                      name="Failure Probability %"
                      stroke="#dc2626"
                      strokeWidth={2}
                      dot={{ fill: '#dc2626' }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-4 grid grid-cols-3 gap-4 text-sm">
                <div className="bg-blue-50 p-3 rounded-lg">
                  <div className="text-blue-600 font-medium">Current</div>
                  <div className="text-2xl font-bold text-blue-900">
                    {selectedConditionForecast.current_condition}
                  </div>
                </div>
                <div className="bg-amber-50 p-3 rounded-lg">
                  <div className="text-amber-600 font-medium">Deterioration</div>
                  <div className="text-2xl font-bold text-amber-900">
                    -{selectedConditionForecast.deterioration_rate}/yr
                  </div>
                </div>
                <div className={`p-3 rounded-lg ${
                  selectedConditionForecast.years_to_failure
                    ? 'bg-red-50'
                    : 'bg-green-50'
                }`}>
                  <div className={`font-medium ${
                    selectedConditionForecast.years_to_failure
                      ? 'text-red-600'
                      : 'text-green-600'
                  }`}>
                    {selectedConditionForecast.years_to_failure ? 'Failure In' : 'Status'}
                  </div>
                  <div className={`text-2xl font-bold ${
                    selectedConditionForecast.years_to_failure
                      ? 'text-red-900'
                      : 'text-green-900'
                  }`}>
                    {selectedConditionForecast.years_to_failure
                      ? `${selectedConditionForecast.years_to_failure} yrs`
                      : 'Stable'}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Demand Forecast Chart */}
          {selectedDemandForecast && demandChartData.length > 0 && (
            <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
              <h3 className="text-lg font-semibold mb-4">
                Demand Forecast: {selectedDemandForecast.asset_id}
              </h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={demandChartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="year" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="demand"
                      name="Projected Demand"
                      stroke="#8b5cf6"
                      strokeWidth={2}
                    />
                    <Line
                      type="monotone"
                      dataKey="capacity"
                      name="Current Capacity"
                      stroke="#10b981"
                      strokeWidth={2}
                      strokeDasharray="5 5"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              {selectedDemandForecast.requires_expansion && (
                <div className="mt-4 bg-amber-50 border border-amber-200 rounded-lg p-3">
                  <div className="flex items-center gap-2 text-amber-800">
                    <AlertTriangle className="w-4 h-4" />
                    <span className="font-medium">Expansion Required</span>
                  </div>
                  <p className="text-sm text-amber-700 mt-1">
                    {selectedDemandForecast.expansion_timeline}
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Bottlenecks Table */}
      {bottlenecks.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="p-4 border-b border-gray-200">
            <h3 className="font-semibold flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-amber-500" />
              Infrastructure Bottlenecks
            </h3>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Asset</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Severity</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Impact</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Priority</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {bottlenecks.map((bottleneck, index) => (
                  <tr key={index} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">
                      {bottleneck.asset_name}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <span className={`px-2 py-1 rounded-full text-xs ${
                        bottleneck.type === 'Capacity' ? 'bg-amber-100 text-amber-800' :
                        bottleneck.type === 'Condition' ? 'bg-red-100 text-red-800' :
                        'bg-blue-100 text-blue-800'
                      }`}>
                        {bottleneck.type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-gray-200 rounded-full h-2">
                          <div
                            className={`h-2 rounded-full ${
                              bottleneck.severity > 0.7 ? 'bg-red-500' :
                              bottleneck.severity > 0.4 ? 'bg-amber-500' :
                              'bg-yellow-500'
                            }`}
                            style={{ width: `${bottleneck.severity * 100}%` }}
                          />
                        </div>
                        <span className="text-gray-600">{(bottleneck.severity * 100).toFixed(0)}%</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600 max-w-xs truncate">
                      {bottleneck.impact}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        bottleneck.priority === 1 ? 'bg-red-100 text-red-800' :
                        'bg-amber-100 text-amber-800'
                      }`}>
                        P{bottleneck.priority}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Empty State */}
      {conditionForecasts.length === 0 && !loading && (
        <div className="bg-gradient-to-br from-gray-50 to-purple-50/30 border-2 border-dashed border-gray-200 rounded-2xl p-12 text-center">
          <div className="w-20 h-20 rounded-2xl bg-purple-100 flex items-center justify-center mx-auto mb-6">
            <TrendingDown className="w-10 h-10 text-purple-600" />
          </div>
          <h3 className="text-xl font-semibold text-gray-700 mb-2">
            Anticipatory Planning
          </h3>
          <p className="text-gray-500 max-w-md mx-auto leading-relaxed">
            Run a forecast to predict infrastructure deterioration, project future demand,
            and identify bottlenecks before they become critical.
          </p>
          <button
            onClick={onRunForecast}
            className="mt-6 bg-gradient-to-r from-purple-600 to-indigo-600 text-white px-8 py-3 rounded-lg hover:shadow-lg transition font-medium"
          >
            Generate Forecast
          </button>
        </div>
      )}
    </div>
  );
};
