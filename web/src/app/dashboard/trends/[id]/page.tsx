"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  Minus,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Info,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { usePatientTrends } from "@/lib/hooks/use-api";
import { TrendSparkline } from "@/components/charts/trend-sparkline";
import type { TrendItem } from "@/lib/api-client";

const DIRECTION_META: Record<
  string,
  { label: string; color: string; bgColor: string; icon: React.ComponentType<{ className?: string }> }
> = {
  improving: {
    label: "Improving",
    color: "text-green-600",
    bgColor: "bg-green-50 dark:bg-green-950",
    icon: TrendingDown,
  },
  stable: {
    label: "Stable",
    color: "text-blue-600",
    bgColor: "bg-blue-50 dark:bg-blue-950",
    icon: Minus,
  },
  worsening: {
    label: "Worsening",
    color: "text-orange-600",
    bgColor: "bg-orange-50 dark:bg-orange-950",
    icon: TrendingUp,
  },
  volatile: {
    label: "Volatile",
    color: "text-red-600",
    bgColor: "bg-red-50 dark:bg-red-950",
    icon: AlertTriangle,
  },
};

function buildSparklineData(trend: TrendItem): { value: number }[] {
  const points: { value: number }[] = [{ value: trend.first_score }];
  if (trend.change_points) {
    for (const cp of trend.change_points) {
      points.push({ value: cp.score });
    }
  }
  points.push({ value: trend.last_score });
  return points;
}

function TrendDetailCard({ trend }: { trend: TrendItem }) {
  const [expanded, setExpanded] = useState(false);
  const meta = DIRECTION_META[trend.trend_direction] || DIRECTION_META.stable;
  const Icon = meta.icon;
  const delta = trend.last_score - trend.first_score;
  const sparkData = buildSparklineData(trend);

  return (
    <Card className="overflow-hidden">
      <div
        className="cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 min-w-0">
              <Icon className={`h-4 w-4 flex-shrink-0 ${meta.color}`} />
              <CardTitle className="text-sm truncate">
                {trend.condition_name}
              </CardTitle>
            </div>
            <div className="flex items-center gap-2">
              {trend.organ_system && (
                <Badge variant="outline" className="text-xs hidden sm:inline-flex">
                  {trend.organ_system}
                </Badge>
              )}
              <Badge className={`${meta.bgColor} ${meta.color} border-0`} variant="secondary">
                {meta.label}
              </Badge>
              {expanded ? (
                <ChevronUp className="h-4 w-4 text-gray-400" />
              ) : (
                <ChevronDown className="h-4 w-4 text-gray-400" />
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent className="pb-3">
          <TrendSparkline dataPoints={sparkData} direction={trend.trend_direction} />
        </CardContent>
      </div>

      {expanded && (
        <CardContent className="pt-0 border-t text-sm space-y-2">
          <div className="grid grid-cols-2 gap-4 pt-3">
            <div>
              <p className="text-gray-500 text-xs">First Score</p>
              <p className="font-mono font-medium">{trend.first_score.toFixed(3)}</p>
            </div>
            <div>
              <p className="text-gray-500 text-xs">Last Score</p>
              <p className="font-mono font-medium">{trend.last_score.toFixed(3)}</p>
            </div>
            <div>
              <p className="text-gray-500 text-xs">Delta</p>
              <p className={`font-mono font-medium ${delta > 0 ? "text-red-600" : delta < 0 ? "text-green-600" : ""}`}>
                {delta > 0 ? "+" : ""}{delta.toFixed(3)}
              </p>
            </div>
            <div>
              <p className="text-gray-500 text-xs">Slope</p>
              <p className="font-mono font-medium">{trend.trend_slope.toFixed(4)}</p>
            </div>
            <div>
              <p className="text-gray-500 text-xs">Sessions Analyzed</p>
              <p className="font-medium">{trend.sessions_analyzed}</p>
            </div>
            {trend.condition_icd10 && (
              <div>
                <p className="text-gray-500 text-xs">ICD-10</p>
                <p className="font-mono text-xs">{trend.condition_icd10}</p>
              </div>
            )}
          </div>
        </CardContent>
      )}
    </Card>
  );
}

export default function TrendsPage() {
  const params = useParams();
  const patientId = params.id as string;
  const { data: trendsData, isLoading, error } = usePatientTrends(patientId);
  const [filter, setFilter] = useState<string | null>(null);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <Skeleton className="h-8 w-48 mb-2" />
          <Skeleton className="h-4 w-64" />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-36" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12 text-gray-500">
        Failed to load trends. {error instanceof Error ? error.message : ""}
      </div>
    );
  }

  const trends = trendsData?.trends || [];
  const summary = trendsData?.summary || { improving: 0, worsening: 0, stable: 0, volatile: 0 };

  const summaryCards = [
    { key: "improving", count: summary.improving, ...DIRECTION_META.improving },
    { key: "stable", count: summary.stable, ...DIRECTION_META.stable },
    { key: "worsening", count: summary.worsening, ...DIRECTION_META.worsening },
    { key: "volatile", count: summary.volatile, ...DIRECTION_META.volatile },
  ];

  // Filter and sort trends by |slope| descending
  const filteredTrends = filter
    ? trends.filter((t) => t.trend_direction === filter)
    : trends;
  const sortedTrends = [...filteredTrends].sort(
    (a, b) => Math.abs(b.trend_slope) - Math.abs(a.trend_slope)
  );

  return (
    <div className="space-y-6">
      <div>
        <Button variant="ghost" size="sm" asChild className="mb-2">
          <Link href="/dashboard">
            <ArrowLeft className="h-4 w-4 mr-1" /> Back
          </Link>
        </Button>
        <h1 className="text-2xl font-bold">Temporal Trends</h1>
        <p className="text-gray-500">
          Condition score changes across scan sessions
        </p>
      </div>

      {/* Empty state */}
      {trends.length === 0 ? (
        <Alert>
          <Info className="h-4 w-4" />
          <AlertDescription>
            Trend analysis requires <strong>2 or more analyzed sessions</strong>{" "}
            for the same patient. Upload and analyze additional scans to see
            how conditions change over time.
          </AlertDescription>
        </Alert>
      ) : (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {summaryCards.map((item) => {
              const Icon = item.icon;
              const isActive = filter === item.key;
              return (
                <Card
                  key={item.key}
                  className={`cursor-pointer transition-all ${
                    isActive ? "ring-2 ring-blue-500" : "hover:shadow-md"
                  }`}
                  onClick={() => setFilter(isActive ? null : item.key)}
                >
                  <CardContent className="pt-6 text-center">
                    <Icon className={`h-8 w-8 mx-auto mb-2 ${item.color}`} />
                    <p className="text-2xl font-bold">{item.count}</p>
                    <p className="text-sm text-gray-500">{item.label}</p>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          {/* Sparkline grid */}
          <Card>
            <CardHeader>
              <CardTitle>
                Condition Trends
                {filter && (
                  <Badge
                    variant="secondary"
                    className="ml-2 cursor-pointer"
                    onClick={() => setFilter(null)}
                  >
                    {filter} x
                  </Badge>
                )}
              </CardTitle>
              <CardDescription>
                {sortedTrends.length} condition{sortedTrends.length !== 1 ? "s" : ""}{" "}
                sorted by magnitude of change. Click to expand details.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {sortedTrends.map((trend) => (
                  <TrendDetailCard key={trend.condition_name} trend={trend} />
                ))}
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
