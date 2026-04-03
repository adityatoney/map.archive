"use client";

import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { Badge } from "@/components/ui/badge";
import type { ScatterPoint } from "@/lib/api-client";

const CLUSTER_COLORS = [
  "#3b82f6", // blue
  "#22c55e", // green
  "#f59e0b", // amber
  "#ef4444", // red
  "#8b5cf6", // violet
  "#06b6d4", // cyan
  "#ec4899", // pink
  "#f97316", // orange
  "#14b8a6", // teal
  "#6366f1", // indigo
];

const NOISE_COLOR = "#9ca3af"; // gray-400

function getClusterColor(clusterId: number): string {
  if (clusterId < 0) return NOISE_COLOR;
  return CLUSTER_COLORS[clusterId % CLUSTER_COLORS.length];
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: { payload: ScatterPoint }[];
}

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div className="bg-white dark:bg-gray-900 border rounded-lg shadow-lg p-3 text-sm max-w-xs">
      <p className="font-medium mb-1">{point.condition_name}</p>
      <div className="space-y-0.5 text-gray-600 dark:text-gray-400">
        <p>Score: <span className="font-mono">{point.score.toFixed(3)}</span></p>
        {point.organ_system && <p>Organ: {point.organ_system}</p>}
        {point.risk_tier && (
          <p>
            Risk:{" "}
            <Badge variant="secondary" className="text-xs py-0">
              {point.risk_tier}
            </Badge>
          </p>
        )}
        <p className="text-xs text-gray-400">
          Cluster {point.cluster_id >= 0 ? point.cluster_id : "Noise"}
        </p>
      </div>
    </div>
  );
}

interface ClusterScatterProps {
  data: ScatterPoint[];
  onPointClick?: (point: ScatterPoint) => void;
  selectedClusterId?: number | null;
  height?: number;
}

export function ClusterScatter({
  data,
  onPointClick,
  selectedClusterId,
  height = 350,
}: ClusterScatterProps) {
  if (!data || data.length === 0) {
    return (
      <div
        className="flex items-center justify-center text-gray-400 text-sm"
        style={{ height }}
      >
        No scatter data available. Run analysis first.
      </div>
    );
  }

  // Group data by cluster_id for distinct colors
  const clusterIds = Array.from(new Set(data.map((d) => d.cluster_id))).sort(
    (a, b) => a - b
  );

  return (
    <div>
      <ResponsiveContainer width="100%" height={height}>
        <ScatterChart margin={{ top: 10, right: 10, bottom: 10, left: 10 }}>
          <XAxis dataKey="x" type="number" hide />
          <YAxis dataKey="y" type="number" hide />
          <Tooltip
            content={<CustomTooltip />}
            cursor={{ strokeDasharray: "3 3" }}
          />
          {clusterIds.map((cid) => {
            const clusterData = data.filter((d) => d.cluster_id === cid);
            const dimmed =
              selectedClusterId !== null &&
              selectedClusterId !== undefined &&
              selectedClusterId !== cid;
            return (
              <Scatter
                key={cid}
                name={`Cluster ${cid >= 0 ? cid : "Noise"}`}
                data={clusterData}
                onClick={(point) => onPointClick?.(point as unknown as ScatterPoint)}
                cursor="pointer"
              >
                {clusterData.map((_, idx) => (
                  <Cell
                    key={idx}
                    fill={getClusterColor(cid)}
                    fillOpacity={dimmed ? 0.15 : 0.8}
                    r={dimmed ? 4 : 6}
                  />
                ))}
              </Scatter>
            );
          })}
        </ScatterChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="flex flex-wrap gap-3 mt-2 px-2 justify-center">
        {clusterIds.map((cid) => (
          <div
            key={cid}
            className="flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-400 cursor-pointer hover:opacity-80"
            onClick={() => onPointClick?.({ cluster_id: cid } as ScatterPoint)}
          >
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: getClusterColor(cid) }}
            />
            {cid >= 0 ? `Cluster ${cid}` : "Noise"}
            <span className="text-gray-400">
              ({data.filter((d) => d.cluster_id === cid).length})
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
