interface LineageEdgeProps {
  fromX: number;
  fromY: number;
  toX: number;
  toY: number;
  relationship: 'version_parent' | 'version_child' | 'derivation_source' | 'derived';
}

export function LineageEdge({
  fromX,
  fromY,
  toX,
  toY,
  relationship,
}: LineageEdgeProps) {
  const isVersion = relationship === 'version_parent' || relationship === 'version_child';

  // Calculate control points for curved line
  const midX = (fromX + toX) / 2;
  const midY = (fromY + toY) / 2;

  // Curve offset based on direction
  const dx = toX - fromX;
  const dy = toY - fromY;
  const curveOffset = Math.min(Math.abs(dx), Math.abs(dy)) * 0.3;

  // Path for curved line
  const path = `M ${fromX} ${fromY} Q ${midX} ${midY - curveOffset} ${toX} ${toY}`;

  // Arrow marker ID
  const markerId = `arrow-${relationship}`;
  const strokeColor = isVersion ? '#9CA3AF' : '#6B7280'; // gray-400 or gray-500

  return (
    <g>
      {/* Define arrow marker */}
      <defs>
        <marker
          id={markerId}
          viewBox="0 0 10 10"
          refX="9"
          refY="5"
          markerWidth="6"
          markerHeight="6"
          orient="auto-start-reverse"
        >
          <path d="M 0 0 L 10 5 L 0 10 z" fill={strokeColor} />
        </marker>
      </defs>

      {/* Edge line */}
      <path
        d={path}
        fill="none"
        stroke={strokeColor}
        strokeWidth={1.5}
        strokeDasharray={isVersion ? '6 3' : undefined}
        markerEnd={`url(#${markerId})`}
      />

      {/* Relationship label (optional, for complex graphs) */}
      {/* <text
        x={midX}
        y={midY - curveOffset - 8}
        fill="#9CA3AF"
        fontSize={10}
        fontFamily="Inter, sans-serif"
        textAnchor="middle"
      >
        {relationship.replace('_', ' ')}
      </text> */}
    </g>
  );
}
