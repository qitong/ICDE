import { useMemo } from 'react';
import { LineageNode } from './LineageNode';
import { LineageEdge } from './LineageEdge';
import type { DatasetLineage, DatasetType, Dataset } from '../../types';

interface LineageGraphProps {
  lineageData: DatasetLineage;
  datasets: Dataset[];
  onNodeClick: (id: string) => void;
}

interface PositionedNode {
  id: string;
  name: string;
  type: DatasetType;
  x: number;
  y: number;
  isFocused: boolean;
  isStale: boolean;
}

interface PositionedEdge {
  id: string;
  fromX: number;
  fromY: number;
  toX: number;
  toY: number;
  relationship: 'version_parent' | 'version_child' | 'derivation_source' | 'derived';
}

const NODE_WIDTH = 140;
const NODE_HEIGHT = 50;
const HORIZONTAL_GAP = 80;
const VERTICAL_GAP = 60;
const CENTER_X = 400;
const CENTER_Y = 200;

export function LineageGraph({ lineageData, datasets, onNodeClick }: LineageGraphProps) {
  // Find dataset by ID to get stale status
  const getDatasetStale = (id: string): boolean => {
    const ds = datasets.find(d => d.id === id);
    return ds?.is_stale ?? false;
  };

  // Calculate node positions
  const { nodes, edges } = useMemo(() => {
    const positionedNodes: PositionedNode[] = [];
    const positionedEdges: PositionedEdge[] = [];

    // Center node (current dataset)
    positionedNodes.push({
      id: lineageData.dataset.id,
      name: lineageData.dataset.name,
      type: lineageData.dataset.type,
      x: CENTER_X,
      y: CENTER_Y,
      isFocused: true,
      isStale: getDatasetStale(lineageData.dataset.id),
    });

    // Separate ancestors by relationship type
    const versionParents = lineageData.ancestors.filter(a => a.relationship === 'version_parent');
    const derivationSources = lineageData.ancestors.filter(a => a.relationship === 'derivation_source');

    // Separate descendants by relationship type
    const versionChildren = lineageData.descendants.filter(d => d.relationship === 'version_child');
    const derivedDatasets = lineageData.descendants.filter(d => d.relationship === 'derived');

    // Position version parents (above center)
    versionParents.forEach((ancestor, index) => {
      const x = CENTER_X;
      const y = CENTER_Y - (index + 1) * (NODE_HEIGHT + VERTICAL_GAP);
      positionedNodes.push({
        id: ancestor.id,
        name: ancestor.name,
        type: ancestor.type,
        x,
        y,
        isFocused: false,
        isStale: getDatasetStale(ancestor.id),
      });
      positionedEdges.push({
        id: `edge-${ancestor.id}-to-center`,
        fromX: x,
        fromY: y + NODE_HEIGHT / 2,
        toX: CENTER_X,
        toY: CENTER_Y - NODE_HEIGHT / 2,
        relationship: 'version_parent',
      });
    });

    // Position derivation sources (left of center)
    derivationSources.forEach((ancestor, index) => {
      const x = CENTER_X - (NODE_WIDTH + HORIZONTAL_GAP);
      const y = CENTER_Y + index * (NODE_HEIGHT + VERTICAL_GAP / 2);
      positionedNodes.push({
        id: ancestor.id,
        name: ancestor.name,
        type: ancestor.type,
        x,
        y,
        isFocused: false,
        isStale: getDatasetStale(ancestor.id),
      });
      positionedEdges.push({
        id: `edge-${ancestor.id}-to-center`,
        fromX: x + NODE_WIDTH / 2,
        fromY: y,
        toX: CENTER_X - NODE_WIDTH / 2,
        toY: CENTER_Y,
        relationship: 'derivation_source',
      });
    });

    // Position version children (below center)
    versionChildren.forEach((descendant, index) => {
      const x = CENTER_X;
      const y = CENTER_Y + (index + 1) * (NODE_HEIGHT + VERTICAL_GAP);
      positionedNodes.push({
        id: descendant.id,
        name: descendant.name,
        type: descendant.type,
        x,
        y,
        isFocused: false,
        isStale: getDatasetStale(descendant.id),
      });
      positionedEdges.push({
        id: `edge-center-to-${descendant.id}`,
        fromX: CENTER_X,
        fromY: CENTER_Y + NODE_HEIGHT / 2,
        toX: x,
        toY: y - NODE_HEIGHT / 2,
        relationship: 'version_child',
      });
    });

    // Position derived datasets (right of center, spread vertically)
    const derivedStartY = CENTER_Y - ((derivedDatasets.length - 1) * (NODE_HEIGHT + VERTICAL_GAP / 2)) / 2;
    derivedDatasets.forEach((descendant, index) => {
      const x = CENTER_X + NODE_WIDTH + HORIZONTAL_GAP;
      const y = derivedStartY + index * (NODE_HEIGHT + VERTICAL_GAP / 2);
      positionedNodes.push({
        id: descendant.id,
        name: descendant.name,
        type: descendant.type,
        x,
        y,
        isFocused: false,
        isStale: getDatasetStale(descendant.id),
      });
      positionedEdges.push({
        id: `edge-center-to-${descendant.id}`,
        fromX: CENTER_X + NODE_WIDTH / 2,
        fromY: CENTER_Y,
        toX: x - NODE_WIDTH / 2,
        toY: y,
        relationship: 'derived',
      });
    });

    return { nodes: positionedNodes, edges: positionedEdges };
  }, [lineageData, datasets]);

  // Calculate viewBox based on node positions
  const viewBox = useMemo(() => {
    if (nodes.length === 0) return '0 0 800 400';

    const padding = 60;
    const xs = nodes.map(n => n.x);
    const ys = nodes.map(n => n.y);
    const minX = Math.min(...xs) - NODE_WIDTH / 2 - padding;
    const maxX = Math.max(...xs) + NODE_WIDTH / 2 + padding;
    const minY = Math.min(...ys) - NODE_HEIGHT / 2 - padding;
    const maxY = Math.max(...ys) + NODE_HEIGHT / 2 + padding;

    return `${minX} ${minY} ${maxX - minX} ${maxY - minY}`;
  }, [nodes]);

  if (nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-muted">
        No lineage data available
      </div>
    );
  }

  return (
    <svg
      viewBox={viewBox}
      className="w-full h-full"
      style={{ minHeight: '300px' }}
    >
      {/* Background grid pattern */}
      <defs>
        <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
          <path
            d="M 40 0 L 0 0 0 40"
            fill="none"
            stroke="#F3F4F6"
            strokeWidth="0.5"
          />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#grid)" />

      {/* Edges (render first, behind nodes) */}
      {edges.map(edge => (
        <LineageEdge
          key={edge.id}
          fromX={edge.fromX}
          fromY={edge.fromY}
          toX={edge.toX}
          toY={edge.toY}
          relationship={edge.relationship}
        />
      ))}

      {/* Nodes */}
      {nodes.map(node => (
        <LineageNode
          key={node.id}
          id={node.id}
          name={node.name}
          type={node.type}
          isFocused={node.isFocused}
          isStale={node.isStale}
          x={node.x}
          y={node.y}
          onClick={onNodeClick}
        />
      ))}

      {/* Legend */}
      <g transform="translate(20, 20)">
        <rect width="160" height="80" rx="4" fill="white" stroke="#E8E8E8" />
        <text x="10" y="18" fontSize="10" fontWeight="600" fill="#0D0D0D">Legend</text>

        {/* RAW */}
        <rect x="10" y="28" width="12" height="12" rx="6" fill="#EFF6FF" stroke="#3B82F6" />
        <text x="28" y="38" fontSize="9" fill="#6B7280">RAW Dataset</text>

        {/* DERIVED */}
        <rect x="10" y="46" width="12" height="12" rx="2" fill="#FFF7ED" stroke="#F97316" />
        <text x="28" y="56" fontSize="9" fill="#6B7280">DERIVED Dataset</text>

        {/* Version line */}
        <line x1="10" y1="68" x2="22" y2="68" stroke="#9CA3AF" strokeDasharray="4 2" />
        <text x="28" y="71" fontSize="9" fill="#6B7280">Version</text>

        {/* Derive line */}
        <line x1="85" y1="68" x2="97" y2="68" stroke="#6B7280" />
        <text x="103" y="71" fontSize="9" fill="#6B7280">Derived</text>
      </g>
    </svg>
  );
}
