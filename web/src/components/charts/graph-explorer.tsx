"use client";

import { useMemo, useState } from "react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { GraphNode, GraphEdge } from "@/lib/api-client";

const NODE_COLORS: Record<string, { fill: string; stroke: string }> = {
  disease: { fill: "#dbeafe", stroke: "#3b82f6" },
  pathway: { fill: "#f3e8ff", stroke: "#8b5cf6" },
  intervention: { fill: "#dcfce7", stroke: "#22c55e" },
  lifestyle: { fill: "#fef3c7", stroke: "#f59e0b" },
};

const EDGE_COLOR = "#d1d5db";
const EDGE_COLOR_HOVER = "#6b7280";

interface PositionedNode extends GraphNode {
  x: number;
  y: number;
  radius: number;
}

interface GraphExplorerProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  width?: number;
  height?: number;
}

function layoutNodes(
  nodes: GraphNode[],
  width: number,
  height: number
): PositionedNode[] {
  const cx = width / 2;
  const cy = height / 2;

  // Separate nodes by type: diseases in center ring, others in outer ring
  const diseases = nodes.filter((n) => n.type === "disease");
  const others = nodes.filter((n) => n.type !== "disease");

  const positioned: PositionedNode[] = [];

  // Disease nodes in inner ring
  const innerRadius = Math.min(width, height) * 0.18;
  diseases.forEach((node, i) => {
    const angle = (2 * Math.PI * i) / Math.max(diseases.length, 1) - Math.PI / 2;
    positioned.push({
      ...node,
      x: cx + innerRadius * Math.cos(angle),
      y: cy + innerRadius * Math.sin(angle),
      radius: 24,
    });
  });

  // Other nodes in outer ring
  const outerRadius = Math.min(width, height) * 0.4;
  others.forEach((node, i) => {
    const angle = (2 * Math.PI * i) / Math.max(others.length, 1) - Math.PI / 2;
    positioned.push({
      ...node,
      x: cx + outerRadius * Math.cos(angle),
      y: cy + outerRadius * Math.sin(angle),
      radius: 18,
    });
  });

  return positioned;
}

function truncate(s: string, max: number): string {
  if (s.length <= max) return s;
  // Try to break at a word boundary
  const trimmed = s.slice(0, max);
  const lastSpace = trimmed.lastIndexOf(" ");
  if (lastSpace > max * 0.5) return trimmed.slice(0, lastSpace) + "\u2026";
  return trimmed + "\u2026";
}

export function GraphExplorer({
  nodes,
  edges,
  width = 600,
  height = 450,
}: GraphExplorerProps) {
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  const positioned = useMemo(
    () => layoutNodes(nodes, width, height),
    [nodes, width, height]
  );

  const nodeMap = useMemo(() => {
    const map: Record<string, PositionedNode> = {};
    for (const n of positioned) map[n.id] = n;
    return map;
  }, [positioned]);

  if (nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400 text-sm">
        No graph data available
      </div>
    );
  }

  // Determine which edges connect to hovered node
  const hoveredEdges = new Set<number>();
  const connectedNodes = new Set<string>();
  if (hoveredNode) {
    connectedNodes.add(hoveredNode);
    edges.forEach((e, idx) => {
      if (e.source === hoveredNode || e.target === hoveredNode) {
        hoveredEdges.add(idx);
        connectedNodes.add(e.source);
        connectedNodes.add(e.target);
      }
    });
  }

  return (
    <TooltipProvider>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full max-h-[450px]"
        style={{ minHeight: 300 }}
      >
        {/* Edges */}
        {edges.map((edge, idx) => {
          const source = nodeMap[edge.source];
          const target = nodeMap[edge.target];
          if (!source || !target) return null;

          const isHighlighted = hoveredEdges.has(idx);
          const isDimmed = hoveredNode && !isHighlighted;

          // Curved bezier path
          const mx = (source.x + target.x) / 2;
          const my = (source.y + target.y) / 2;
          const dx = target.x - source.x;
          const dy = target.y - source.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          const offset = Math.min(dist * 0.15, 30);
          // Perpendicular offset for curve
          const nx = -dy / (dist || 1) * offset;
          const ny = dx / (dist || 1) * offset;

          return (
            <path
              key={idx}
              d={`M ${source.x} ${source.y} Q ${mx + nx} ${my + ny} ${target.x} ${target.y}`}
              fill="none"
              stroke={isHighlighted ? EDGE_COLOR_HOVER : EDGE_COLOR}
              strokeWidth={isHighlighted ? 2 : 1}
              opacity={isDimmed ? 0.15 : 0.6}
              className="transition-all duration-150"
            />
          );
        })}

        {/* Nodes */}
        {positioned.map((node) => {
          const colors = NODE_COLORS[node.type] || NODE_COLORS.pathway;
          const isDimmed = hoveredNode && !connectedNodes.has(node.id);
          const isHovered = hoveredNode === node.id;

          return (
            <Tooltip key={node.id}>
              <TooltipTrigger asChild>
                <g
                  onMouseEnter={() => setHoveredNode(node.id)}
                  onMouseLeave={() => setHoveredNode(null)}
                  className="cursor-pointer"
                >
                  <circle
                    cx={node.x}
                    cy={node.y}
                    r={node.radius}
                    fill={colors.fill}
                    stroke={isHovered ? "#2563eb" : colors.stroke}
                    strokeWidth={isHovered ? 2.5 : 1.5}
                    opacity={isDimmed ? 0.2 : 1}
                    className="transition-all duration-150"
                  />
                  <text
                    x={node.x}
                    y={node.y + 3}
                    textAnchor="middle"
                    className="text-[8px] fill-gray-700 dark:fill-gray-300 pointer-events-none font-medium select-none"
                    opacity={isDimmed ? 0.2 : 1}
                  >
                    {truncate(node.label, node.type === "disease" ? 16 : 14)}
                  </text>
                </g>
              </TooltipTrigger>
              <TooltipContent>
                <div className="text-sm">
                  <p className="font-medium">{node.label}</p>
                  <p className="text-xs text-gray-500 capitalize">{node.type}</p>
                </div>
              </TooltipContent>
            </Tooltip>
          );
        })}
      </svg>

      {/* Legend */}
      <div className="flex flex-wrap gap-4 mt-3 justify-center">
        {Object.entries(NODE_COLORS).map(([type, colors]) => (
          <div key={type} className="flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-400">
            <div
              className="w-3 h-3 rounded-full border"
              style={{ backgroundColor: colors.fill, borderColor: colors.stroke }}
            />
            <span className="capitalize">{type}</span>
          </div>
        ))}
      </div>
    </TooltipProvider>
  );
}
