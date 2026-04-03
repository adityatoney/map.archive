"use client";

import { useState } from "react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Badge } from "@/components/ui/badge";

interface OrganRisk {
  avg_score: number;
  condition_count: number;
  risk_tier: string;
}

interface BodyMapProps {
  riskSummary: Record<string, OrganRisk>;
  onOrganClick?: (organ: string) => void;
}

const RISK_COLORS: Record<string, { fill: string; stroke: string }> = {
  critical: { fill: "#fca5a5", stroke: "#dc2626" },
  high: { fill: "#fdba74", stroke: "#ea580c" },
  moderate: { fill: "#fde68a", stroke: "#d97706" },
  low: { fill: "#bbf7d0", stroke: "#16a34a" },
};

const DEFAULT_COLOR = { fill: "#e5e7eb", stroke: "#9ca3af" };

// Map organ system names to SVG region definitions
// Each region: { cx, cy, rx, ry } for ellipses or a path
const ORGAN_REGIONS: Record<string, { cx: number; cy: number; rx: number; ry: number; label: string }> = {
  "Nervous System":          { cx: 150, cy: 45,  rx: 35, ry: 35,  label: "Brain" },
  "Endocrine System":        { cx: 150, cy: 100, rx: 20, ry: 12,  label: "Thyroid" },
  "Respiratory System":      { cx: 150, cy: 155, rx: 50, ry: 30,  label: "Lungs" },
  "Cardiovascular System":   { cx: 150, cy: 195, rx: 25, ry: 25,  label: "Heart" },
  "Digestive System":        { cx: 130, cy: 260, rx: 35, ry: 35,  label: "Stomach" },
  "Hepatobiliary System":    { cx: 185, cy: 240, rx: 25, ry: 20,  label: "Liver" },
  "Urinary System":          { cx: 150, cy: 310, rx: 30, ry: 18,  label: "Kidneys" },
  "Reproductive System":     { cx: 150, cy: 350, rx: 25, ry: 15,  label: "Reproductive" },
  "Musculoskeletal System":  { cx: 70,  cy: 280, rx: 20, ry: 55,  label: "Muscles" },
  "Immune System":           { cx: 230, cy: 190, rx: 18, ry: 18,  label: "Immune" },
  "Integumentary System":    { cx: 230, cy: 280, rx: 20, ry: 55,  label: "Skin" },
  "Hematologic System":      { cx: 70,  cy: 190, rx: 18, ry: 18,  label: "Blood" },
};

// Fuzzy match organ names from backend to our region keys
function matchOrgan(organName: string): string | null {
  const lower = organName.toLowerCase();
  for (const key of Object.keys(ORGAN_REGIONS)) {
    if (lower.includes(key.toLowerCase().split(" ")[0])) return key;
  }
  // Common aliases
  if (lower.includes("brain") || lower.includes("neuro")) return "Nervous System";
  if (lower.includes("liver") || lower.includes("hepat")) return "Hepatobiliary System";
  if (lower.includes("heart") || lower.includes("cardio") || lower.includes("vascular")) return "Cardiovascular System";
  if (lower.includes("lung") || lower.includes("respir") || lower.includes("pulmon")) return "Respiratory System";
  if (lower.includes("gastr") || lower.includes("digest") || lower.includes("intestin")) return "Digestive System";
  if (lower.includes("kidney") || lower.includes("renal") || lower.includes("urin")) return "Urinary System";
  if (lower.includes("bone") || lower.includes("muscl") || lower.includes("musculo") || lower.includes("skelet")) return "Musculoskeletal System";
  if (lower.includes("skin") || lower.includes("integument") || lower.includes("derma")) return "Integumentary System";
  if (lower.includes("immune") || lower.includes("lymph")) return "Immune System";
  if (lower.includes("blood") || lower.includes("hemato")) return "Hematologic System";
  if (lower.includes("thyroid") || lower.includes("endocrin") || lower.includes("hormon")) return "Endocrine System";
  if (lower.includes("reproduc") || lower.includes("genit")) return "Reproductive System";
  return null;
}

export function BodyMap({ riskSummary, onOrganClick }: BodyMapProps) {
  const [hoveredOrgan, setHoveredOrgan] = useState<string | null>(null);

  // Map risk data to organ regions
  const organRiskMap: Record<string, OrganRisk> = {};
  for (const [organName, data] of Object.entries(riskSummary)) {
    const matched = matchOrgan(organName);
    if (matched) {
      organRiskMap[matched] = data;
    }
  }

  return (
    <TooltipProvider>
      <svg viewBox="0 0 300 420" className="w-full max-w-[300px] mx-auto">
        {/* Body outline */}
        <ellipse cx={150} cy={45} rx={28} ry={30} fill="none" stroke="#d1d5db" strokeWidth={1} />
        {/* Neck */}
        <rect x={142} y={72} width={16} height={18} rx={4} fill="none" stroke="#d1d5db" strokeWidth={1} />
        {/* Torso */}
        <path
          d="M 90 90 Q 85 180 90 300 Q 100 340 150 350 Q 200 340 210 300 Q 215 180 210 90 Z"
          fill="none"
          stroke="#d1d5db"
          strokeWidth={1}
        />
        {/* Arms */}
        <path d="M 90 100 Q 50 140 40 230 Q 38 250 45 260" fill="none" stroke="#d1d5db" strokeWidth={1} />
        <path d="M 210 100 Q 250 140 260 230 Q 262 250 255 260" fill="none" stroke="#d1d5db" strokeWidth={1} />
        {/* Legs */}
        <path d="M 110 340 Q 105 370 100 420" fill="none" stroke="#d1d5db" strokeWidth={1} />
        <path d="M 190 340 Q 195 370 200 420" fill="none" stroke="#d1d5db" strokeWidth={1} />

        {/* Organ regions */}
        {Object.entries(ORGAN_REGIONS).map(([organKey, region]) => {
          const risk = organRiskMap[organKey];
          const colors = risk
            ? RISK_COLORS[risk.risk_tier] || DEFAULT_COLOR
            : DEFAULT_COLOR;
          const isHovered = hoveredOrgan === organKey;

          return (
            <Tooltip key={organKey}>
              <TooltipTrigger asChild>
                <ellipse
                  cx={region.cx}
                  cy={region.cy}
                  rx={region.rx}
                  ry={region.ry}
                  fill={colors.fill}
                  stroke={isHovered ? "#2563eb" : colors.stroke}
                  strokeWidth={isHovered ? 2.5 : 1.5}
                  opacity={risk ? 0.85 : 0.3}
                  className="cursor-pointer transition-all duration-150"
                  onMouseEnter={() => setHoveredOrgan(organKey)}
                  onMouseLeave={() => setHoveredOrgan(null)}
                  onClick={() => onOrganClick?.(organKey)}
                />
              </TooltipTrigger>
              <TooltipContent side="right">
                <div className="text-sm">
                  <p className="font-medium">{region.label}</p>
                  {risk ? (
                    <div className="space-y-0.5">
                      <p className="text-xs text-gray-500">
                        {risk.condition_count} condition{risk.condition_count !== 1 ? "s" : ""} |
                        avg: {risk.avg_score.toFixed(3)}
                      </p>
                      <Badge variant="secondary" className="text-xs">
                        {risk.risk_tier}
                      </Badge>
                    </div>
                  ) : (
                    <p className="text-xs text-gray-400">No data</p>
                  )}
                </div>
              </TooltipContent>
            </Tooltip>
          );
        })}

        {/* Labels for organs with data */}
        {Object.entries(ORGAN_REGIONS).map(([organKey, region]) => {
          const risk = organRiskMap[organKey];
          if (!risk) return null;
          return (
            <text
              key={`label-${organKey}`}
              x={region.cx}
              y={region.cy + 3}
              textAnchor="middle"
              className="text-[8px] fill-gray-700 dark:fill-gray-300 pointer-events-none font-medium"
            >
              {region.label}
            </text>
          );
        })}
      </svg>
    </TooltipProvider>
  );
}
