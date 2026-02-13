import { Database, FunctionSquare, AlertTriangle } from 'lucide-react';
import type { DatasetType } from '../../types';

interface LineageNodeProps {
  id: string;
  name: string;
  type: DatasetType;
  isFocused: boolean;
  isStale?: boolean;
  x: number;
  y: number;
  onClick: (id: string) => void;
}

const NODE_WIDTH = 140;
const NODE_HEIGHT = 50;

export function LineageNode({
  id,
  name,
  type,
  isFocused,
  isStale,
  x,
  y,
  onClick,
}: LineageNodeProps) {
  const isRaw = type === 'RAW';

  // Colors based on type and state
  const getFillColor = () => {
    if (isFocused) return '#E42313'; // primary color
    return isRaw ? '#EFF6FF' : '#FFF7ED'; // blue-50 or orange-50
  };

  const getStrokeColor = () => {
    if (isFocused) return '#E42313';
    if (isStale) return '#F59E0B'; // amber-500
    return isRaw ? '#3B82F6' : '#F97316'; // blue-500 or orange-500
  };

  const getTextColor = () => {
    if (isFocused) return '#FFFFFF';
    return '#0D0D0D';
  };

  const getIconColor = () => {
    if (isFocused) return '#FFFFFF';
    return isRaw ? '#3B82F6' : '#F97316';
  };

  // Truncate long names
  const displayName = name.length > 16 ? name.slice(0, 14) + '...' : name;

  return (
    <g
      className="cursor-pointer transition-transform hover:scale-105"
      transform={`translate(${x - NODE_WIDTH / 2}, ${y - NODE_HEIGHT / 2})`}
      onClick={() => onClick(id)}
    >
      {/* Node shape */}
      <rect
        width={NODE_WIDTH}
        height={NODE_HEIGHT}
        rx={isRaw ? 25 : 8}
        fill={getFillColor()}
        stroke={getStrokeColor()}
        strokeWidth={isFocused ? 2.5 : 1.5}
        strokeDasharray={isStale ? '4 2' : undefined}
      />

      {/* Icon */}
      <g transform="translate(12, 13)">
        {isRaw ? (
          <Database size={24} color={getIconColor()} />
        ) : (
          <FunctionSquare size={24} color={getIconColor()} />
        )}
      </g>

      {/* Name */}
      <text
        x={44}
        y={NODE_HEIGHT / 2 + 5}
        fill={getTextColor()}
        fontSize={12}
        fontFamily="Inter, sans-serif"
        fontWeight={isFocused ? 600 : 400}
      >
        {displayName}
      </text>

      {/* Stale indicator */}
      {isStale && (
        <g transform={`translate(${NODE_WIDTH - 20}, 4)`}>
          <AlertTriangle size={14} color="#F59E0B" />
        </g>
      )}

      {/* Type badge */}
      <g transform={`translate(${NODE_WIDTH - 36}, ${NODE_HEIGHT - 16})`}>
        <rect
          width={28}
          height={12}
          rx={2}
          fill={isFocused ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.05)'}
        />
        <text
          x={14}
          y={9}
          fill={getTextColor()}
          fontSize={8}
          fontFamily="Inter, sans-serif"
          textAnchor="middle"
          opacity={0.7}
        >
          {type}
        </text>
      </g>
    </g>
  );
}
