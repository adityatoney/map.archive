"use client";

import { LineChart, Line, ResponsiveContainer, YAxis } from "recharts";

const DIRECTION_COLORS: Record<string, string> = {
  improving: "#22c55e",
  worsening: "#ef4444",
  stable: "#3b82f6",
  volatile: "#f59e0b",
};

interface TrendSparklineProps {
  dataPoints: { value: number }[];
  direction: string;
  height?: number;
}

export function TrendSparkline({
  dataPoints,
  direction,
  height = 48,
}: TrendSparklineProps) {
  const color = DIRECTION_COLORS[direction] || "#6b7280";

  if (dataPoints.length < 2) {
    return (
      <div
        className="flex items-center justify-center text-gray-400 text-xs"
        style={{ height }}
      >
        Insufficient data
      </div>
    );
  }

  const scores = dataPoints.map((p) => p.value);
  const min = Math.min(...scores);
  const max = Math.max(...scores);
  const padding = (max - min) * 0.1 || 0.01;

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={dataPoints}>
        <YAxis domain={[min - padding, max + padding]} hide />
        <Line
          type="monotone"
          dataKey="value"
          stroke={color}
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
