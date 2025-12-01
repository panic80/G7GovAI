import React from 'react';
import { FileSearch, FileCode, Settings2, UserCheck, Scale, BookMarked } from 'lucide-react';
import { StepCard } from './StepCard';
import { StepData, LexGraphNodeName } from '../../types';

interface StepProgressProps {
  stepData: StepData;
  language?: string;
}

interface StepConfig {
  key: LexGraphNodeName;
  title: string;
  titleFr: string;
  icon: React.ComponentType<{ size?: string | number; className?: string }>;
}

const STEPS: StepConfig[] = [
  { key: 'retrieve', title: 'Retrieving Documents', titleFr: 'Recherche de documents', icon: FileSearch },
  { key: 'extract_rules', title: 'Extracting Rules', titleFr: 'Extraction des règles', icon: FileCode },
  { key: 'resolve_thresholds', title: 'Resolving Thresholds', titleFr: 'Résolution des seuils', icon: Settings2 },
  { key: 'map_legislation', title: 'Mapping Legislation', titleFr: 'Cartographie législative', icon: BookMarked },
  { key: 'extract_facts', title: 'Extracting Facts', titleFr: 'Extraction des faits', icon: UserCheck },
  { key: 'evaluate', title: 'Evaluating Rules', titleFr: 'Évaluation des règles', icon: Scale },
];

function generateSummary(key: LexGraphNodeName, data: StepData[LexGraphNodeName], language: string): string {
  const isFr = language === 'fr';

  switch (key) {
    case 'retrieve': {
      const d = data as StepData['retrieve'];
      const count = d.documents?.length || 0;
      return isFr ? `${count} documents trouvés` : `Found ${count} documents`;
    }
    case 'extract_rules': {
      const d = data as StepData['extract_rules'];
      const count = d.rules?.length || 0;
      return isFr ? `${count} règles extraites` : `Extracted ${count} rules`;
    }
    case 'resolve_thresholds': {
      const d = data as StepData['resolve_thresholds'];
      const { high = 0, medium = 0, low = 0 } = d.confidenceCounts || {};
      return `${high} HIGH, ${medium} MED, ${low} LOW`;
    }
    case 'map_legislation': {
      const d = data as StepData['map_legislation'];
      const map = d.legislationMap;
      if (!map) return isFr ? 'Aucune législation' : 'No legislation';
      const total = (map.primary?.length || 0) + (map.related?.length || 0) + (map.definitions?.length || 0);
      return isFr ? `${total} extraits législatifs` : `${total} legislative excerpts`;
    }
    case 'extract_facts': {
      const d = data as StepData['extract_facts'];
      const facts = d.facts || {};
      const entries = Object.entries(facts).slice(0, 2);
      if (entries.length === 0) return isFr ? 'Aucun fait' : 'No facts';
      return entries.map(([k, v]) => `${k}=${v}`).join(', ');
    }
    case 'evaluate': {
      const d = data as StepData['evaluate'];
      if (d.decision) {
        return d.decision.eligible
          ? (isFr ? 'ADMISSIBLE' : 'ELIGIBLE')
          : (isFr ? 'NON ADMISSIBLE' : 'INELIGIBLE');
      }
      return '';
    }
    default:
      return '';
  }
}

export const StepProgress: React.FC<StepProgressProps> = ({ stepData, language = 'en' }) => {
  const isFr = language === 'fr';

  return (
    <div className="space-y-2">
      {STEPS.map((step, idx) => {
        const data = stepData[step.key];
        const summary = data.status === 'completed' ? generateSummary(step.key, data, language) : undefined;

        return (
          <StepCard
            key={step.key}
            stepNumber={idx + 1}
            title={isFr ? step.titleFr : step.title}
            icon={step.icon}
            status={data.status}
            summary={summary}
          >
            {/* Detailed content for each step when expanded */}
            {step.key === 'retrieve' && (data as StepData['retrieve']).documents?.length > 0 && (
              <ul className="list-disc pl-4 mt-2 space-y-1">
                {(data as StepData['retrieve']).documents.slice(0, 3).map((doc, i) => (
                  <li key={i} className="text-xs truncate" title={doc}>
                    {doc.slice(0, 80)}...
                  </li>
                ))}
                {(data as StepData['retrieve']).documents.length > 3 && (
                  <li className="text-xs text-gray-400">
                    +{(data as StepData['retrieve']).documents.length - 3} {isFr ? 'autres' : 'more'}
                  </li>
                )}
              </ul>
            )}

            {step.key === 'extract_rules' && (data as StepData['extract_rules']).rules?.length > 0 && (
              <ul className="list-disc pl-4 mt-2 space-y-1">
                {(data as StepData['extract_rules']).rules.slice(0, 3).map((rule, i) => (
                  <li key={i} className="text-xs">
                    <span className="font-medium">{rule.rule_id}:</span>{' '}
                    {rule.description?.slice(0, 50)}...
                  </li>
                ))}
              </ul>
            )}

            {step.key === 'resolve_thresholds' && (
              <div className="mt-2 flex gap-2 text-xs">
                <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded">
                  {(data as StepData['resolve_thresholds']).confidenceCounts?.high || 0} HIGH
                </span>
                <span className="px-2 py-0.5 bg-yellow-100 text-yellow-700 rounded">
                  {(data as StepData['resolve_thresholds']).confidenceCounts?.medium || 0} MED
                </span>
                <span className="px-2 py-0.5 bg-red-100 text-red-700 rounded">
                  {(data as StepData['resolve_thresholds']).confidenceCounts?.low || 0} LOW
                </span>
              </div>
            )}

            {step.key === 'extract_facts' && Object.keys((data as StepData['extract_facts']).facts || {}).length > 0 && (
              <div className="mt-2 grid grid-cols-2 gap-1 text-xs">
                {Object.entries((data as StepData['extract_facts']).facts).map(([k, v]) => (
                  <div key={k} className="bg-gray-100 px-2 py-1 rounded truncate" title={`${k}: ${v}`}>
                    <span className="font-medium">{k}:</span> {String(v)}
                  </div>
                ))}
              </div>
            )}

            {step.key === 'evaluate' && (data as StepData['evaluate']).decision && (
              <div className="mt-2">
                <div
                  className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium ${
                    (data as StepData['evaluate']).decision?.eligible
                      ? 'bg-green-100 text-green-800'
                      : 'bg-red-100 text-red-800'
                  }`}
                >
                  {(data as StepData['evaluate']).decision?.eligible
                    ? (isFr ? 'ADMISSIBLE' : 'ELIGIBLE')
                    : (isFr ? 'NON ADMISSIBLE' : 'INELIGIBLE')}
                </div>
              </div>
            )}
          </StepCard>
        );
      })}
    </div>
  );
};
