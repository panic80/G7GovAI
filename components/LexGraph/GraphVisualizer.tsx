import React, { useRef, useState, useEffect } from 'react';
import { Network, FileText } from 'lucide-react';
import ForceGraph2D from 'react-force-graph-2d';
import { GraphData, StepData } from '../../types';
import { StepProgress } from './StepProgress';
import { useLanguage } from '../../contexts/LanguageContext';

interface GraphVisualizerProps {
  graphData: GraphData;
  stepData: StepData;
  loading: boolean;
}

export const GraphVisualizer: React.FC<GraphVisualizerProps> = ({
  graphData,
  stepData,
  loading,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState<{ width: number; height: number } | null>(null);
  const { language } = useLanguage();

  // Measure container dimensions after mount
  useEffect(() => {
    if (containerRef.current) {
      const { clientWidth, clientHeight } = containerRef.current;
      setDimensions({ width: clientWidth, height: clientHeight });
    }
  }, []);

  // Check if any evaluation has started
  const hasStarted = stepData.retrieve.status !== 'pending';
  // Check if rules have been extracted (graph should have data after resolve_thresholds)
  const hasRules = stepData.resolve_thresholds.status === 'completed';

  return (
    <div className="flex gap-4 h-full flex-grow">
      {/* Left Sidebar: Progress Steps */}
      <div className="w-72 flex-shrink-0 bg-white rounded-xl p-4 border border-gray-200 overflow-y-auto">
        <h3 className="text-sm font-semibold mb-3 text-gray-700 flex items-center gap-2">
          <FileText size={16} />
          {language === 'fr' ? 'Progression du Graphe' : 'Graph Building Progress'}
        </h3>
        {hasStarted ? (
          <StepProgress stepData={stepData} language={language} />
        ) : (
          <div className="text-sm text-gray-400 text-center py-8">
            <Network size={32} className="mx-auto mb-3 opacity-30" />
            <p className="mb-2">
              {language === 'fr'
                ? "Lancez une evaluation dans l'onglet Rule Evaluator pour construire le graphe."
                : 'Run an evaluation in the Rule Evaluator tab to build the graph.'}
            </p>
            <p className="text-xs text-gray-300">
              {language === 'fr'
                ? 'Le graphe sera construit au fur et a mesure que les regles sont extraites.'
                : 'The graph will build as rules are extracted.'}
            </p>
          </div>
        )}
      </div>

      {/* Right: Graph Visualization */}
      <div
        className="flex-grow bg-gray-900 rounded-xl overflow-hidden relative"
        ref={containerRef}
      >
        {graphData.nodes.length === 0 ? (
          <div className="absolute inset-0 flex items-center justify-center text-white/50">
            <div className="text-center max-w-md px-8">
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-white mx-auto mb-4" />
                  <p className="text-lg mb-2">
                    {language === 'fr'
                      ? 'Construction du graphe a partir des regles...'
                      : 'Building graph from extracted rules...'}
                  </p>
                  <p className="text-sm opacity-60">
                    {language === 'fr'
                      ? 'Les noeuds apparaitront apres l\'extraction des regles.'
                      : 'Nodes will appear after rules are extracted.'}
                  </p>
                </>
              ) : hasStarted && !hasRules ? (
                <>
                  <div className="animate-pulse">
                    <Network size={48} className="mx-auto mb-4 opacity-50" />
                  </div>
                  <p className="text-lg mb-2">
                    {language === 'fr' ? 'En attente des regles...' : 'Waiting for rules...'}
                  </p>
                  <p className="text-sm opacity-60">
                    {language === 'fr'
                      ? 'Le graphe sera genere une fois les regles extraites et resolues.'
                      : 'Graph will be generated once rules are extracted and resolved.'}
                  </p>
                </>
              ) : (
                <>
                  <Network size={48} className="mx-auto mb-4 opacity-30" />
                  <p className="text-lg mb-2">
                    {language === 'fr' ? 'Pas de donnees de graphe' : 'No graph data yet'}
                  </p>
                  <p className="text-sm opacity-60">
                    {language === 'fr'
                      ? 'Lancez une evaluation pour voir le graphe des regles se construire en temps reel.'
                      : 'Run an evaluation to see the rules graph build in real-time.'}
                  </p>
                </>
              )}
            </div>
          </div>
        ) : dimensions ? (
          <ForceGraph2D
            width={dimensions.width}
            height={dimensions.height}
            graphData={graphData}
            nodeLabel="label"
            nodeColor={(node: { group?: number }) =>
              node.group === 1 ? '#4299e1' : '#ef4444'
            } // Blue for rules, Red for conditions
            nodeRelSize={6}
            linkColor={() => 'rgba(255,255,255,0.2)'}
            linkDirectionalArrowLength={3.5}
            linkDirectionalArrowRelPos={1}
            backgroundColor="#111827"
            nodeCanvasObject={(node: { x?: number; y?: number; label?: string; group?: number }, ctx, globalScale) => {
              const label = node.label || '';
              const fontSize = 12 / globalScale;
              ctx.font = `${fontSize}px Sans-Serif`;
              const textWidth = ctx.measureText(label).width;
              const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.2);

              // Draw node circle
              ctx.beginPath();
              ctx.arc(node.x || 0, node.y || 0, 6, 0, 2 * Math.PI, false);
              ctx.fillStyle = node.group === 1 ? '#4299e1' : '#ef4444';
              ctx.fill();

              // Draw label background
              ctx.fillStyle = 'rgba(17, 24, 39, 0.8)';
              ctx.fillRect(
                (node.x || 0) - bckgDimensions[0] / 2,
                (node.y || 0) + 8,
                bckgDimensions[0],
                bckgDimensions[1]
              );

              // Draw label text
              ctx.textAlign = 'center';
              ctx.textBaseline = 'middle';
              ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
              ctx.fillText(label, node.x || 0, (node.y || 0) + 8 + fontSize / 2);
            }}
          />
        ) : null}

        {/* Legend */}
        {graphData.nodes.length > 0 && (
          <div className="absolute bottom-4 right-4 bg-gray-800/90 rounded-lg p-3 text-xs text-white">
            <div className="flex items-center gap-2 mb-1">
              <div className="w-3 h-3 rounded-full bg-blue-500" />
              <span>{language === 'fr' ? 'Regles' : 'Rules'}</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-red-500" />
              <span>{language === 'fr' ? 'Conditions' : 'Conditions'}</span>
            </div>
            <div className="mt-2 pt-2 border-t border-gray-700 text-gray-400">
              {graphData.nodes.length} {language === 'fr' ? 'noeuds' : 'nodes'}, {graphData.links.length} {language === 'fr' ? 'liens' : 'links'}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
