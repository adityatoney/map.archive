"use client";

import { useState, useMemo } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Network, AlertTriangle, Shield, Zap } from "lucide-react";
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
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useInsights, useGraphContext } from "@/lib/hooks/use-api";
import { ClusterScatter } from "@/components/charts/cluster-scatter";
import { GraphExplorer } from "@/components/charts/graph-explorer";
import type { ScatterPoint } from "@/lib/api-client";

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

function ConfidenceBar({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100);
  const color =
    confidence >= 0.7
      ? "bg-green-500"
      : confidence >= 0.5
        ? "bg-amber-500"
        : "bg-gray-400";
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div className="flex items-center gap-2">
            <div className="w-16 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${color}`}
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="text-xs text-gray-400">{pct}%</span>
          </div>
        </TooltipTrigger>
        <TooltipContent>
          <p>
            Confidence: {pct}% — based on semantic similarity
            {confidence > 0.5 ? " + shared biological pathways" : ""}
          </p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

export default function InsightsPage() {
  const params = useParams();
  const sessionId = params.id as string;
  const { data: insights, isLoading, error } = useInsights(sessionId);
  const [selectedClusterId, setSelectedClusterId] = useState<number | null>(null);

  // ICD-10 codes + condition names for KG explorer — provided by the backend
  const icdCodes = useMemo(() => insights?.icd_codes || [], [insights]);
  const conditionNames = useMemo(
    () => insights?.condition_names_for_icd || [],
    [insights]
  );

  // Use graph context for KG explorer (only if we have ICD codes)
  const { data: graphData } = useGraphContext(icdCodes, conditionNames);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-80" />
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

  // Filter clusters if a cluster is selected from scatter plot
  const displayedClusters =
    selectedClusterId !== null
      ? insights.clusters.filter((c) => c.cluster_id === selectedClusterId)
      : insights.clusters;

  function handleScatterClick(point: ScatterPoint) {
    if (selectedClusterId === point.cluster_id) {
      setSelectedClusterId(null);
    } else {
      setSelectedClusterId(point.cluster_id);
    }
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

      {/* UMAP Cluster Scatter Plot */}
      {insights.scatter_data && insights.scatter_data.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Condition Cluster Map</CardTitle>
                <CardDescription>
                  UMAP 2D projection of condition embeddings — click a cluster to filter
                </CardDescription>
              </div>
              {selectedClusterId !== null && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setSelectedClusterId(null)}
                >
                  Clear filter
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent>
            <ClusterScatter
              data={insights.scatter_data}
              onPointClick={handleScatterClick}
              selectedClusterId={selectedClusterId}
            />
          </CardContent>
        </Card>
      )}

      {/* Cluster cards */}
      <Card>
        <CardHeader>
          <CardTitle>
            Condition Clusters
            {selectedClusterId !== null && (
              <Badge variant="secondary" className="ml-2">
                Filtered: Cluster {selectedClusterId}
              </Badge>
            )}
          </CardTitle>
          <CardDescription>
            Groups of related conditions identified by embedding similarity
          </CardDescription>
        </CardHeader>
        <CardContent>
          {displayedClusters.length === 0 ? (
            <p className="text-gray-400 text-sm">
              {selectedClusterId !== null
                ? "No cluster matches the selection."
                : "No clusters generated yet. Run analysis first."}
            </p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {displayedClusters.map((cluster) => (
                <Card
                  key={cluster.cluster_id}
                  className={`transition-all ${
                    selectedClusterId === cluster.cluster_id
                      ? "ring-2 ring-blue-500"
                      : ""
                  }`}
                >
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm">
                        Cluster {cluster.cluster_id}
                      </CardTitle>
                      <div className="flex items-center gap-2">
                        <ConfidenceBar confidence={cluster.confidence} />
                        {cluster.risk_tier && (
                          <RiskBadge tier={cluster.risk_tier} />
                        )}
                      </div>
                    </div>
                    <CardDescription>
                      {cluster.conditions.length} conditions | avg score:{" "}
                      {cluster.avg_score.toFixed(3)}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <ul className="text-sm space-y-1">
                      {cluster.conditions.slice(0, 5).map((c) => (
                        <li
                          key={c}
                          className="text-gray-600 dark:text-gray-400"
                        >
                          {c}
                        </li>
                      ))}
                      {cluster.conditions.length > 5 && (
                        <li className="text-gray-400 text-xs">
                          +{cluster.conditions.length - 5} more
                        </li>
                      )}
                    </ul>

                    {/* Shared pathways */}
                    {cluster.shared_pathways.length > 0 && (
                      <div className="pt-2 border-t">
                        <p className="text-xs font-medium text-gray-500 mb-1 flex items-center gap-1">
                          <Zap className="h-3 w-3" /> Shared Pathways
                        </p>
                        <div className="flex flex-wrap gap-1">
                          {cluster.shared_pathways.map((pw) => (
                            <Badge
                              key={pw}
                              variant="outline"
                              className="text-xs"
                            >
                              {pw}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Systemic patterns */}
      {insights.patterns.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              Systemic Patterns
            </CardTitle>
            <CardDescription>
              Condition pairs sharing biological pathways in the knowledge graph
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {insights.patterns.slice(0, 10).map((pattern, idx) => (
                <div key={idx} className="p-3 border rounded-md">
                  <div className="flex items-center justify-between mb-1">
                    <p className="font-medium text-sm">{pattern.pattern_name}</p>
                    <span className="text-xs text-gray-400">
                      confidence: {(pattern.confidence_score * 100).toFixed(0)}%
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mb-2">
                    {pattern.description}
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {pattern.shared_pathways.map((pw) => (
                      <Badge key={pw} variant="outline" className="text-xs">
                        {pw}
                      </Badge>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Knowledge Graph Explorer */}
      <Card>
        <CardHeader>
          <CardTitle>Knowledge Graph Explorer</CardTitle>
          <CardDescription>
            Interactive network of conditions, pathways, and interventions
          </CardDescription>
        </CardHeader>
        <CardContent>
          {graphData && graphData.nodes.length > 0 ? (
            <GraphExplorer nodes={graphData.nodes} edges={graphData.edges} />
          ) : (
            <div className="flex items-center justify-center h-64 bg-gray-50 dark:bg-gray-800/50 rounded-md">
              <div className="text-center text-gray-400">
                <Network className="h-12 w-12 mx-auto mb-2 opacity-30" />
                <p className="text-sm">
                  {icdCodes.length === 0
                    ? "Knowledge graph visualization requires ICD-10 coded conditions"
                    : "Loading graph data..."}
                </p>
              </div>
            </div>
          )}
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
