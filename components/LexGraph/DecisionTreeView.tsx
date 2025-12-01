'use client';

import React, { useCallback, useRef, useState } from 'react';
import Tree, { RawNodeDatum, CustomNodeElementProps } from 'react-d3-tree';
import { DecisionTreeNode, LegislativeExcerpt } from '../../types';
import { CheckCircle, XCircle, Circle, BookOpen, ChevronDown, ChevronUp } from 'lucide-react';

interface DecisionTreeViewProps {
  tree: DecisionTreeNode;
  onExcerptClick: (excerpt: LegislativeExcerpt) => void;
}

// Convert our DecisionTreeNode to react-d3-tree's RawNodeDatum format
function convertToTreeData(node: DecisionTreeNode): RawNodeDatum {
  return {
    name: node.label,
    attributes: {
      type: node.type,
      result: node.result || 'unknown',
      condition_text: node.condition_text || '',
      citation: node.legislative_excerpt?.citation || '',
    },
    children: node.children?.map(convertToTreeData),
    // Store original node data for reference
    __original: node,
  } as RawNodeDatum & { __original: DecisionTreeNode };
}

// Custom node component
const CustomNode: React.FC<CustomNodeElementProps & { onExcerptClick: (excerpt: LegislativeExcerpt) => void }> = ({
  nodeDatum,
  onExcerptClick,
}) => {
  const [expanded, setExpanded] = useState(false);
  const nodeData = nodeDatum as RawNodeDatum & { __original?: DecisionTreeNode };
  const original = nodeData.__original;
  const result = nodeDatum.attributes?.result as string;
  const type = nodeDatum.attributes?.type as string;
  const citation = nodeDatum.attributes?.citation as string;

  // Colors based on result
  const getBgColor = () => {
    if (type === 'decision') {
      return result === 'pass' ? 'bg-green-100 border-green-500' : 'bg-red-100 border-red-500';
    }
    switch (result) {
      case 'pass': return 'bg-green-50 border-green-400';
      case 'fail': return 'bg-red-50 border-red-400';
      default: return 'bg-gray-50 border-gray-300';
    }
  };

  const getIcon = () => {
    if (type === 'decision') {
      return result === 'pass'
        ? <CheckCircle className="w-6 h-6 text-green-600" />
        : <XCircle className="w-6 h-6 text-red-600" />;
    }
    switch (result) {
      case 'pass': return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'fail': return <XCircle className="w-5 h-5 text-red-500" />;
      default: return <Circle className="w-5 h-5 text-gray-400" />;
    }
  };

  const handleExcerptClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (original?.legislative_excerpt) {
      onExcerptClick(original.legislative_excerpt);
    }
  };

  return (
    <g>
      <foreignObject width={280} height={expanded ? 200 : 100} x={-140} y={-50}>
        <div
          className={`p-3 rounded-lg border-2 shadow-sm ${getBgColor()} cursor-pointer transition-all`}
          onClick={() => setExpanded(!expanded)}
        >
          {/* Header */}
          <div className="flex items-start gap-2">
            {getIcon()}
            <div className="flex-1 min-w-0">
              <p className={`text-sm font-medium text-gray-900 ${type === 'decision' ? 'text-lg' : ''}`}>
                {nodeDatum.name}
              </p>
              {citation && (
                <button
                  onClick={handleExcerptClick}
                  className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1 mt-1"
                >
                  <BookOpen className="w-3 h-3" />
                  {citation}
                </button>
              )}
            </div>
            {original?.legislative_excerpt && (
              expanded ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />
            )}
          </div>

          {/* Expanded content */}
          {expanded && original?.legislative_excerpt && (
            <div className="mt-2 pt-2 border-t border-gray-200">
              <p className="text-xs text-gray-600 line-clamp-3">
                {original.legislative_excerpt.plain_language || original.legislative_excerpt.text.slice(0, 150) + '...'}
              </p>
              {original.legislative_excerpt.confidence && (
                <span className={`inline-block mt-1 text-xs px-2 py-0.5 rounded ${
                  original.legislative_excerpt.confidence === 'HIGH' ? 'bg-green-200 text-green-800' :
                  original.legislative_excerpt.confidence === 'MEDIUM' ? 'bg-yellow-200 text-yellow-800' :
                  'bg-gray-200 text-gray-800'
                }`}>
                  {original.legislative_excerpt.confidence}
                </span>
              )}
            </div>
          )}
        </div>
      </foreignObject>
    </g>
  );
};

export const DecisionTreeView: React.FC<DecisionTreeViewProps> = ({ tree, onExcerptClick }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState<{ width: number; height: number } | null>(null);

  // Update dimensions on mount - only render Tree after container is measured
  React.useEffect(() => {
    if (containerRef.current) {
      const { width, height } = containerRef.current.getBoundingClientRect();
      setDimensions({ width, height });
    }
  }, []);

  const treeData = convertToTreeData(tree);

  // Custom render function that passes onExcerptClick
  const renderCustomNode = useCallback((props: CustomNodeElementProps) => (
    <CustomNode {...props} onExcerptClick={onExcerptClick} />
  ), [onExcerptClick]);

  return (
    <div ref={containerRef} className="w-full h-[600px] bg-white rounded-lg border border-gray-200">
      {dimensions && (
        <Tree
          data={treeData}
          orientation="vertical"
          pathFunc="step"
          translate={{ x: dimensions.width / 2, y: 80 }}
          separation={{ siblings: 2, nonSiblings: 2.5 }}
          nodeSize={{ x: 300, y: 150 }}
          renderCustomNodeElement={renderCustomNode}
          zoom={0.8}
          scaleExtent={{ min: 0.3, max: 2 }}
          enableLegacyTransitions
          transitionDuration={300}
        />
      )}
    </div>
  );
};

export default DecisionTreeView;
