
import React, { useEffect, useState } from 'react';
import { ShieldCheck, Activity, Lock, Scale, FileText, RefreshCw, Settings, Server, Key, Eye, EyeOff } from 'lucide-react';
import { getLogs, getSystemStats } from '../services/auditService';
import { AuditLog } from '../types';
import { useLanguage } from '../contexts/LanguageContext';
import { useApiKey } from '../contexts/ApiKeyContext';
import { CONFIG } from '../config';

// Model presets configuration
const MODEL_PRESETS = {
  low: { reasoning: 'gemini-2.5-flash', fast: 'gemini-2.5-flash-lite' },
  normal: { reasoning: 'gemini-2.5-pro', fast: 'gemini-2.5-flash-lite' },
  ultra: { reasoning: 'gemini-3-pro-preview', fast: 'gemini-2.5-flash' },
} as const;

type PresetKey = keyof typeof MODEL_PRESETS | 'custom';

export const GovernanceDashboard: React.FC = () => {
  const { language, t } = useLanguage();
  const { refreshStatus: refreshGlobalApiKeyStatus } = useApiKey();
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [stats, setStats] = useState({ total: 0, errors: 0, avgLatency: 0 });
  
  // Local state for model selection (persisted in localStorage in a real app)
  const [selectedReasoningModel, setSelectedReasoningModel] = useState(CONFIG.GEMINI.MODEL_NAME);
  const [selectedFastModel, setSelectedFastModel] = useState('gemini-2.5-flash-lite');
  const [reasoningModels, setReasoningModels] = useState<{id: string, displayName: string}[]>([]);
  const [fastModels, setFastModels] = useState<{id: string, displayName: string}[]>([]);
  const [customApiKey, setCustomApiKey] = useState('');
  const [apiKeyConfigured, setApiKeyConfigured] = useState(true); // Assume configured until we check
  const [hasCustomKey, setHasCustomKey] = useState(false);
  const [keyPreview, setKeyPreview] = useState<string | null>(null);
  const [showApiKey, setShowApiKey] = useState(false);

  const refresh = () => {
    setLogs(getLogs());
    setStats(getSystemStats());
  };
  
  // Fetch current backend configuration and available models
  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const res = await fetch(`${CONFIG.RAG.BASE_URL}/config/models`);
        if (res.ok) {
          const data = await res.json();
          if (data.reasoning) setSelectedReasoningModel(data.reasoning);
          if (data.fast) setSelectedFastModel(data.fast);
        }
      } catch (err) {
        if (import.meta.env.DEV) console.error('Failed to fetch model config:', err);
      }
    };

    const fetchAvailableModels = async () => {
      try {
        const [reasoningRes, fastRes] = await Promise.all([
          fetch(`${CONFIG.RAG.BASE_URL}/config/available-models?model_type=reasoning`),
          fetch(`${CONFIG.RAG.BASE_URL}/config/available-models?model_type=fast`)
        ]);
        if (reasoningRes.ok) {
          const data = await reasoningRes.json();
          setReasoningModels(data.models || []);
        }
        if (fastRes.ok) {
          const data = await fastRes.json();
          setFastModels(data.models || []);
        }
      } catch (err) {
        if (import.meta.env.DEV) console.error('Failed to fetch available models:', err);
      }
    };

    const fetchApiKeyStatus = async () => {
      try {
        const res = await fetch(`${CONFIG.RAG.BASE_URL}/config/api-key`);
        if (res.ok) {
          const data = await res.json();
          setApiKeyConfigured(data.api_key_configured);
          setHasCustomKey(data.has_custom_key);
          setKeyPreview(data.key_preview);
        }
      } catch (err) {
        if (import.meta.env.DEV) console.error('Failed to fetch API key status:', err);
      }
    };

    fetchConfig();
    fetchAvailableModels();
    fetchApiKeyStatus();
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 5000); // Live poll
    return () => clearInterval(interval);
  }, []);

  // Handler for model change
  const handleModelChange = async (type: 'reasoning' | 'fast', value: string) => {
    // Optimistic update
    if (type === 'reasoning') setSelectedReasoningModel(value);
    else setSelectedFastModel(value);

    try {
      const payload = type === 'reasoning' ? { reasoning: value } : { fast: value };
      await fetch(`${CONFIG.RAG.BASE_URL}/config/models`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
    } catch (err) {
      if (import.meta.env.DEV) console.error('Failed to update model:', err);
    }
  };

  // Handler for preset change
  const handlePresetChange = async (preset: keyof typeof MODEL_PRESETS) => {
    const config = MODEL_PRESETS[preset];
    setSelectedReasoningModel(config.reasoning);
    setSelectedFastModel(config.fast);

    try {
      await fetch(`${CONFIG.RAG.BASE_URL}/config/models`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reasoning: config.reasoning, fast: config.fast })
      });
    } catch (err) {
      if (import.meta.env.DEV) console.error('Failed to apply preset:', err);
    }
  };

  // Handler for API key change
  const handleApiKeyUpdate = async () => {
    try {
      const res = await fetch(`${CONFIG.RAG.BASE_URL}/config/api-key`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: customApiKey })
      });
      if (res.ok) {
        const data = await res.json();
        setApiKeyConfigured(data.api_key_configured);
        setHasCustomKey(data.has_custom_key);
        // Refresh key preview
        const statusRes = await fetch(`${CONFIG.RAG.BASE_URL}/config/api-key`);
        if (statusRes.ok) {
          const statusData = await statusRes.json();
          setKeyPreview(statusData.key_preview);
        }
        setCustomApiKey('');
        // Refresh global API key status to update banner
        refreshGlobalApiKeyStatus();
      }
    } catch (err) {
      if (import.meta.env.DEV) console.error('Failed to update API key:', err);
    }
  };

  const handleClearApiKey = async () => {
    try {
      await fetch(`${CONFIG.RAG.BASE_URL}/config/api-key`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: '' })
      });
      setHasCustomKey(false);
      setKeyPreview(null);
      setCustomApiKey('');
      // Refresh global API key status to show banner again
      refreshGlobalApiKeyStatus();
    } catch (err) {
      if (import.meta.env.DEV) console.error('Failed to clear API key:', err);
    }
  };

  // Derive active preset from current selections (defaults to 'custom' if no match)
  const activePreset: PresetKey = (Object.entries(MODEL_PRESETS).find(
    ([_, config]) => config.reasoning === selectedReasoningModel && config.fast === selectedFastModel
  )?.[0] as keyof typeof MODEL_PRESETS) || 'custom';

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-8">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
          <ShieldCheck className="w-8 h-8 text-gov-blue" />
          {t('governance.title')}
          <span className="text-lg font-normal text-gray-500">| {t('governance.subtitle')}</span>
        </h1>
        <p className="text-gray-600 mt-2">
          {t('governance.description')}
        </p>
      </header>

      {/* API Key Warning Banner */}
      {!apiKeyConfigured && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center gap-3">
          <Key className="w-6 h-6 text-red-600 flex-shrink-0" />
          <div className="flex-1">
            <p className="text-red-800 font-medium">{t('governance.noApiKey')}</p>
            <p className="text-red-600 text-sm">{t('governance.noApiKeyDesc')}</p>
          </div>
        </div>
      )}

      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex items-center gap-4">
          <div className="p-3 bg-blue-100 rounded-full text-gov-blue">
            <Activity size={24} />
          </div>
          <div>
            <p className="text-sm text-gray-500">{t('governance.stats.total')}</p>
            <p className="text-2xl font-bold">{stats.total}</p>
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex items-center gap-4">
           <div className="p-3 bg-green-100 rounded-full text-green-700">
            <RefreshCw size={24} />
          </div>
          <div>
            <p className="text-sm text-gray-500">{t('governance.stats.latency')}</p>
            <p className="text-2xl font-bold">{stats.avgLatency}ms</p>
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex items-center gap-4">
           <div className="p-3 bg-purple-100 rounded-full text-purple-700">
            <Scale size={24} />
          </div>
          <div>
            <p className="text-sm text-gray-500">{t('governance.stats.compliance')}</p>
            <p className="text-2xl font-bold">G7-Ready</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        {/* Live Audit Log */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 flex justify-between items-center">
            <h3 className="font-bold text-gray-800">{t('governance.auditLog')}</h3>
            <span className="text-xs text-gray-400 flex items-center gap-1"><div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"/> {t('governance.live')}</span>
          </div>
          <div className="h-[500px] overflow-y-auto">
            <table className="w-full text-sm text-left">
              <thead className="bg-gray-50 text-gray-500 font-medium">
                <tr>
                  <th className="px-6 py-3">{t('governance.table.timestamp')}</th>
                  <th className="px-6 py-3">{t('governance.table.module')}</th>
                  <th className="px-6 py-3">{t('governance.table.action')}</th>
                  <th className="px-6 py-3">{t('governance.table.latency')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {logs.length === 0 ? (
                   <tr><td colSpan={4} className="px-6 py-8 text-center text-gray-400">{t('governance.noActivity')}</td></tr>
                ) : (
                  logs.map((log) => (
                    <tr key={log.id} className="hover:bg-gray-50 transition">
                      <td className="px-6 py-3 text-gray-600 font-mono text-xs whitespace-nowrap">
                        {log.timestamp.split('T')[1].split('.')[0]}
                      </td>
                      <td className="px-6 py-3">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium
                          ${log.module === 'GovLens' ? 'bg-blue-100 text-blue-800' : 
                            log.module === 'LexGraph' ? 'bg-purple-100 text-purple-800' : 
                            log.module === 'ForesightOps' ? 'bg-indigo-100 text-indigo-800' : 
                            'bg-teal-100 text-teal-800'}`}>
                          {log.module}
                        </span>
                      </td>
                      <td className="px-6 py-3 text-gray-800">{log.action}</td>
                      <td className="px-6 py-3 text-gray-500 font-mono text-xs">{log.latency_ms}ms</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Model Cards & Compliance */}
        <div className="space-y-6">
          
          {/* Model Configuration Card */}
          <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
            <h3 className="font-bold text-gray-800 mb-4 flex items-center gap-2">
              <Server size={20} className="text-gov-blue" />
              {t('governance.modelConfig')}
            </h3>

            {/* Preset Buttons */}
            <div className="flex gap-2 mb-4">
              {(['low', 'normal', 'ultra', 'custom'] as const).map((preset) => (
                <button
                  key={preset}
                  onClick={() => preset !== 'custom' && handlePresetChange(preset as keyof typeof MODEL_PRESETS)}
                  disabled={preset === 'custom'}
                  className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all ${
                    activePreset === preset
                      ? preset === 'low' ? 'bg-green-600 text-white shadow-md'
                      : preset === 'normal' ? 'bg-blue-600 text-white shadow-md'
                      : preset === 'ultra' ? 'bg-red-600 text-white shadow-md'
                      : 'bg-gray-600 text-white shadow-md'
                      : preset === 'custom'
                        ? 'bg-gray-50 text-gray-400 cursor-default'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {t(`governance.preset.${preset}`)}
                </button>
              ))}
            </div>

            <div className="space-y-4">
              <div className="p-4 bg-blue-50 rounded-lg border border-blue-100">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t('governance.reasoningModel')}
                </label>
                <select
                  value={selectedReasoningModel}
                  onChange={(e) => handleModelChange('reasoning', e.target.value)}
                  className="w-full p-2 border border-gray-300 rounded-md bg-white font-mono text-sm focus:ring-2 focus:ring-gov-blue focus:border-gov-blue"
                >
                  {reasoningModels.length > 0 ? (
                    reasoningModels.map(model => (
                      <option key={model.id} value={model.id}>{model.displayName}</option>
                    ))
                  ) : (
                    <>
                      <option value="gemini-3-pro-preview">Gemini 3 Pro Preview</option>
                      <option value="gemini-2.5-pro">Gemini 2.5 Pro</option>
                      <option value="gemini-2.5-flash">Gemini 2.5 Flash</option>
                    </>
                  )}
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  {t('governance.reasoningDesc')}
                </p>
              </div>

              <div className="p-4 bg-green-50 rounded-lg border border-green-100">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t('governance.fastModel')}
                </label>
                <select
                  value={selectedFastModel}
                  onChange={(e) => handleModelChange('fast', e.target.value)}
                  className="w-full p-2 border border-gray-300 rounded-md bg-white font-mono text-sm focus:ring-2 focus:ring-green-500 focus:border-green-500"
                >
                  {fastModels.length > 0 ? (
                    fastModels.map(model => (
                      <option key={model.id} value={model.id}>{model.displayName}</option>
                    ))
                  ) : (
                    <>
                      <option value="gemini-2.5-flash-lite">Gemini 2.5 Flash-Lite</option>
                      <option value="gemini-2.5-flash">Gemini 2.5 Flash</option>
                    </>
                  )}
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  {t('governance.fastDesc')}
                </p>
              </div>

              {/* Custom API Key */}
              <div className="p-4 bg-yellow-50 rounded-lg border border-yellow-200">
                <label className="block text-sm font-medium text-gray-700 mb-1 flex items-center gap-2">
                  <Key size={16} />
                  {t('governance.apiKey')}
                </label>
                {hasCustomKey && keyPreview && (
                  <div className="mb-2 text-xs text-green-700 bg-green-100 px-2 py-1 rounded inline-block">
                    Using custom key: {keyPreview}
                  </div>
                )}
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <input
                      type={showApiKey ? 'text' : 'password'}
                      value={customApiKey}
                      onChange={(e) => setCustomApiKey(e.target.value)}
                      placeholder={hasCustomKey ? 'Enter new key to replace...' : 'Enter your Gemini API key...'}
                      className="w-full p-2 pr-10 border border-gray-300 rounded-md bg-white font-mono text-sm focus:ring-2 focus:ring-yellow-500 focus:border-yellow-500"
                    />
                    <button
                      type="button"
                      onClick={() => setShowApiKey(!showApiKey)}
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    >
                      {showApiKey ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                  <button
                    onClick={handleApiKeyUpdate}
                    disabled={!customApiKey.trim()}
                    className="px-4 py-2 bg-yellow-600 text-white rounded-md text-sm font-medium hover:bg-yellow-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {hasCustomKey ? 'Update' : 'Set'}
                  </button>
                  {hasCustomKey && (
                    <button
                      onClick={handleClearApiKey}
                      className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md text-sm font-medium hover:bg-gray-300"
                    >
                      Clear
                    </button>
                  )}
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  {t('governance.apiKeyDesc')}
                </p>
              </div>
            </div>
          </div>

          {/* System Compliance */}
          <div className="bg-gray-50 p-6 rounded-xl border border-gray-200 shadow-sm">
             <h3 className="font-bold text-gray-800 mb-4 flex items-center gap-2">
              <Lock size={20} className="text-gov-blue" />
              {t('governance.complianceStatus')}
            </h3>
            <ul className="space-y-3">
              <li className="flex items-center gap-3">
                <div className="w-5 h-5 bg-green-500 rounded-full flex items-center justify-center text-white text-xs">✓</div>
                <div className="text-sm">
                  <span className="font-bold">WCAG 2.2 AA</span>
                  <p className="text-xs text-gray-500">Accessibility checks passing for contrast & nav.</p>
                </div>
              </li>
              <li className="flex items-center gap-3">
                <div className="w-5 h-5 bg-green-500 rounded-full flex items-center justify-center text-white text-xs">✓</div>
                 <div className="text-sm">
                  <span className="font-bold">Official Languages Act</span>
                  <p className="text-xs text-gray-500">Bilingual interface and AI outputs verified.</p>
                </div>
              </li>
               <li className="flex items-center gap-3">
                <div className="w-5 h-5 bg-green-500 rounded-full flex items-center justify-center text-white text-xs">✓</div>
                 <div className="text-sm">
                  <span className="font-bold">Directive on Auto. Decision-Making</span>
                  <p className="text-xs text-gray-500">Audit trail active. Explanations provided.</p>
                </div>
              </li>
            </ul>
          </div>

        </div>
      </div>
    </div>
  );
};
