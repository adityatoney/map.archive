"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Network, AlertTriangle } from "lucide-react";
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
import { useInsights } from "@/lib/hooks/use-api";

function RiskBadge({ tier }: { tier: string }) {
  const colors: Record<string, string> = {
    low: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
    moderate: "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200",
    high: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200",
    critical: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
  };
  return (
    <Badge className={colors[tier] || ""} variant="secondary">
      {tier}
    </Badge>
  );
}

export default function InsightsPage() {
  const params = useParams();
  const sessionId = params.id as string;
  const { data: insights, isLoading, error } = useInsights(sessionId);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-48" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !insights) {
    return (
      <div className="text-center py-12 text-gray-500">
        Insights not available. Run analysis first.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <Button variant="ghost" size="sm" asChild className="mb-2">
          <Link href={`/dashboard/report/${sessionId}`}>
            <ArrowLeft className="h-4 w-4 mr-1" /> Back to Report
          </Link>
        </Button>
        <h1 className="text-2xl font-bold">Diagnostic Insights</h1>
        <p className="text-gray-500">
          Pattern analysis and condition correlations
        </p>
      </div>

      {/* Risk summary by organ system */}
      <Card>
        <CardHeader>
          <CardTitle>Organ System Risk Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {Object.entries(insights.risk_summary).map(([organ, data]) => (
              <div
                key={organ}
                className="flex items-center justify-between p-3 border rounded-md"
              >
                <div>
                  <p className="font-medium text-sm">{organ}</p>
                  <p className="text-xs text-gray-500">
                    {data.condition_count} conditions | avg:{" "}
                    {data.avg_score.toFixed(3)}
                  </p>
                </div>
                <RiskBadge tier={data.risk_tier} />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Cluster cards */}
      <Card>
        <CardHeader>
          <CardTitle>Condition Clusters</CardTitle>
          <CardDescription>
            Groups of related conditions identified by embedding similarity
          </CardDescription>
        </CardHeader>
        <CardContent>
          {insights.clusters.length === 0 ? (
            <p className="text-gray-400 text-sm">
              No clusters generated yet. Run analysis first.
            </p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {insights.clusters.map((cluster) => (
                <Card key={cluster.cluster_id}>
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm">
                        Cluster {cluster.cluster_id}
                      </CardTitle>
                      {cluster.risk_tier && (
                        <RiskBadge tier={cluster.risk_tier} />
                      )}
                    </div>
                    <CardDescription>
                      {cluster.conditions.length} conditions | avg score:{" "}
                      {cluster.avg_score.toFixed(3)}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <ul className="text-sm space-y-1">
                      {cluster.conditions.slice(0, 5).map((c) => (
                        <li key={c} className="text-gray-600 dark:text-gray-400">
                          {c}
                        </li>
                      ))}
                      {cluster.conditions.length > 5 && (
                        <li className="text-gray-400 text-xs">
                          +{cluster.conditions.length - 5} more
                        </li>
                      )}
                    </ul>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Knowledge graph explorer placeholder */}
      <Card>
        <CardHeader>
          <CardTitle>Knowledge Graph Explorer</CardTitle>
          <CardDescription>
            Interactive force-directed graph of conditions, pathways, and
            interventions
          </CardDescription>
        </CardHeader>
        <CardContent className="flex items-center justify-center h-64 bg-gray-50 dark:bg-gray-800/50 rounded-md">
          <div className="text-center text-gray-400">
            <Network className="h-12 w-12 mx-auto mb-2 opacity-30" />
            <p className="text-sm">
              D3.js force-directed graph — coming in Phase 5
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Disclaimer */}
      <Alert>
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription className="text-xs">
          {insights.disclaimer}
        </AlertDescription>
      </Alert>
    </div>
  );
}
