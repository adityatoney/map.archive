"use client";

import { useState, useEffect } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Settings,
  Save,
  RotateCcw,
  AlertTriangle,
  CheckCircle2,
  Info,
} from "lucide-react";
import { useRiskConfig, useUpdateRiskConfig } from "@/lib/hooks/use-api";

const TIER_ORDER = ["critical", "high", "moderate", "low"] as const;

const TIER_COLORS: Record<string, string> = {
  critical: "bg-red-500",
  high: "bg-orange-500",
  moderate: "bg-amber-500",
  low: "bg-green-500",
};

const TIER_DESCRIPTIONS: Record<string, string> = {
  critical: "Immediate attention required",
  high: "Significant concern, monitor closely",
  moderate: "Mild concern, routine monitoring",
  low: "Within normal range",
};

const DEFAULT_THRESHOLDS: Record<string, [number, number]> = {
  critical: [0.0, 0.1],
  high: [0.1, 0.2],
  moderate: [0.2, 0.4],
  low: [0.4, 1.01],
};

export default function SettingsPage() {
  const { data: config, isLoading, error } = useRiskConfig();
  const updateConfig = useUpdateRiskConfig();

  const [scoreMode, setScoreMode] = useState<"inverted" | "normal">("inverted");
  const [thresholds, setThresholds] = useState<
    Record<string, [number, number]>
  >(DEFAULT_THRESHOLDS);
  const [configName, setConfigName] = useState("Default");
  const [hasChanges, setHasChanges] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Sync from server data
  useEffect(() => {
    if (config) {
      setScoreMode(config.score_mode);
      setThresholds(config.tier_thresholds);
      setConfigName(config.name);
      setHasChanges(false);
    }
  }, [config]);

  // Track changes
  useEffect(() => {
    if (!config) return;
    const changed =
      scoreMode !== config.score_mode ||
      configName !== config.name ||
      JSON.stringify(thresholds) !== JSON.stringify(config.tier_thresholds);
    setHasChanges(changed);
  }, [scoreMode, thresholds, configName, config]);

  function handleThresholdChange(
    tier: string,
    index: 0 | 1,
    value: string
  ) {
    const num = parseFloat(value);
    if (isNaN(num)) return;
    setThresholds((prev) => ({
      ...prev,
      [tier]: [
        index === 0 ? num : prev[tier][0],
        index === 1 ? num : prev[tier][1],
      ] as [number, number],
    }));
  }

  function handleReset() {
    if (config) {
      setScoreMode(config.score_mode);
      setThresholds(config.tier_thresholds);
      setConfigName(config.name);
    }
  }

  function handleResetDefaults() {
    setScoreMode("inverted");
    setThresholds(DEFAULT_THRESHOLDS);
    setConfigName("Default");
  }

  async function handleSave() {
    setSaveSuccess(false);
    try {
      await updateConfig.mutateAsync({
        score_mode: scoreMode,
        tier_thresholds: thresholds,
        name: configName,
      });
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch {
      // Error handled by mutation state
    }
  }

  // Validate that thresholds cover [0, 1+] without gaps
  function validateThresholds(): string | null {
    for (const tier of TIER_ORDER) {
      const bounds = thresholds[tier];
      if (!bounds || bounds.length !== 2) return `${tier}: invalid bounds`;
      if (bounds[0] >= bounds[1]) return `${tier}: lower must be < upper`;
      if (bounds[0] < 0) return `${tier}: lower bound cannot be negative`;
    }
    // Check for gaps or overlaps
    const sorted = [...TIER_ORDER]
      .map((t) => ({ tier: t, bounds: thresholds[t] }))
      .sort((a, b) => a.bounds[0] - b.bounds[0]);
    for (let i = 1; i < sorted.length; i++) {
      const prevUpper = sorted[i - 1].bounds[1];
      const currLower = sorted[i].bounds[0];
      if (Math.abs(prevUpper - currLower) > 0.001) {
        return `Gap/overlap between ${sorted[i - 1].tier} and ${sorted[i].tier}`;
      }
    }
    return null;
  }

  const validationError = validateThresholds();

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Settings className="h-6 w-6" />
          Settings
        </h1>
        <Card>
          <CardContent className="p-8">
            <div className="flex items-center justify-center text-gray-500">
              Loading configuration...
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Settings className="h-6 w-6" />
          Settings
        </h1>
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            Failed to load risk configuration: {error.message}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Settings className="h-6 w-6" />
          Settings
        </h1>
        {hasChanges && (
          <Badge variant="outline" className="text-amber-600 border-amber-300">
            Unsaved changes
          </Badge>
        )}
      </div>

      {/* Score Interpretation Mode */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Score Interpretation</CardTitle>
          <CardDescription>
            How raw scan scores map to risk levels. MedBed devices use
            &quot;inverted&quot; scoring where lower values indicate higher risk.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-2">
            <Label htmlFor="score-mode">Score Mode</Label>
            <Select
              value={scoreMode}
              onValueChange={(v) =>
                setScoreMode(v as "inverted" | "normal")
              }
            >
              <SelectTrigger id="score-mode" className="w-64">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="inverted">
                  Inverted (lower = higher risk)
                </SelectItem>
                <SelectItem value="normal">
                  Normal (higher = higher risk)
                </SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {scoreMode === "inverted"
                ? "Scores near 0.0 indicate critical risk; scores above 0.5 indicate low risk."
                : "Scores near 1.0 indicate critical risk; scores near 0.0 indicate low risk."}
            </p>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="config-name">Configuration Name</Label>
            <Input
              id="config-name"
              value={configName}
              onChange={(e) => setConfigName(e.target.value)}
              className="w-64"
              placeholder="e.g., Default, Custom v2"
            />
          </div>
        </CardContent>
      </Card>

      {/* Risk Tier Thresholds */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Risk Tier Thresholds</CardTitle>
          <CardDescription>
            Define score ranges for each risk tier. Ranges must be contiguous
            (no gaps or overlaps) and cover the full score spectrum.
            {scoreMode === "inverted" && (
              <span className="block mt-1 text-amber-600 dark:text-amber-400">
                Inverted mode: lower score ranges correspond to higher risk
                tiers.
              </span>
            )}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {TIER_ORDER.map((tier) => (
            <div key={tier} className="flex items-center gap-4">
              <div className="flex items-center gap-2 w-32">
                <div
                  className={`h-3 w-3 rounded-full ${TIER_COLORS[tier]}`}
                />
                <span className="text-sm font-medium capitalize">{tier}</span>
              </div>
              <div className="flex items-center gap-2">
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  max="1.5"
                  value={thresholds[tier]?.[0] ?? 0}
                  onChange={(e) =>
                    handleThresholdChange(tier, 0, e.target.value)
                  }
                  className="w-24 text-center"
                />
                <span className="text-gray-400">to</span>
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  max="1.5"
                  value={thresholds[tier]?.[1] ?? 1}
                  onChange={(e) =>
                    handleThresholdChange(tier, 1, e.target.value)
                  }
                  className="w-24 text-center"
                />
              </div>
              <span className="text-xs text-gray-500 dark:text-gray-400 hidden sm:inline">
                {TIER_DESCRIPTIONS[tier]}
              </span>
            </div>
          ))}

          {validationError && (
            <Alert variant="destructive" className="mt-4">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>{validationError}</AlertDescription>
            </Alert>
          )}

          {/* Visual preview bar */}
          <Separator className="my-4" />
          <div>
            <Label className="text-xs text-gray-500 mb-2 block">
              Threshold Preview
            </Label>
            <div className="flex h-6 rounded-md overflow-hidden border">
              {TIER_ORDER.map((tier) => {
                const [lo, hi] = thresholds[tier] || [0, 0];
                const widthPct = Math.max((hi - lo) * 100, 0);
                return (
                  <div
                    key={tier}
                    className={`${TIER_COLORS[tier]} flex items-center justify-center text-[10px] text-white font-medium`}
                    style={{ width: `${widthPct}%` }}
                    title={`${tier}: ${lo} - ${hi}`}
                  >
                    {widthPct > 8 ? tier : ""}
                  </div>
                );
              })}
            </div>
            <div className="flex justify-between text-[10px] text-gray-400 mt-1">
              <span>0.0 (highest risk)</span>
              <span>1.0 (lowest risk)</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Info Card */}
      <Card className="border-blue-200 dark:border-blue-800 bg-blue-50/50 dark:bg-blue-950/20">
        <CardContent className="flex gap-3 pt-6">
          <Info className="h-5 w-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-blue-900 dark:text-blue-200 space-y-1">
            <p className="font-medium">How changes take effect</p>
            <ul className="list-disc list-inside text-xs space-y-1 text-blue-800 dark:text-blue-300">
              <li>
                Changes apply immediately to all new API responses (risk tiers
                are computed at read time).
              </li>
              <li>
                Existing reports will show updated tier labels without
                re-analysis.
              </li>
              <li>
                Composite risk scores (organ-level) use a normalized formula
                and are not affected by threshold changes.
              </li>
              <li>
                To fully recompute risk with the new config, re-analyze the
                session from the report page.
              </li>
            </ul>
          </div>
        </CardContent>
      </Card>

      {/* Action buttons */}
      <div className="flex items-center gap-3">
        <Button
          onClick={handleSave}
          disabled={
            !hasChanges || !!validationError || updateConfig.isPending
          }
        >
          <Save className="h-4 w-4 mr-2" />
          {updateConfig.isPending ? "Saving..." : "Save Changes"}
        </Button>
        <Button
          variant="outline"
          onClick={handleReset}
          disabled={!hasChanges}
        >
          <RotateCcw className="h-4 w-4 mr-2" />
          Discard
        </Button>
        <Button variant="ghost" onClick={handleResetDefaults}>
          Reset to Defaults
        </Button>

        {saveSuccess && (
          <span className="flex items-center gap-1 text-sm text-green-600 dark:text-green-400">
            <CheckCircle2 className="h-4 w-4" />
            Saved successfully
          </span>
        )}
        {updateConfig.isError && (
          <span className="text-sm text-red-600 dark:text-red-400">
            Error:{" "}
            {updateConfig.error instanceof Error
              ? updateConfig.error.message
              : "Failed to save"}
          </span>
        )}
      </div>
    </div>
  );
}
