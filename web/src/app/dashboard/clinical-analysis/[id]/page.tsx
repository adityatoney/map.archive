"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  ArrowRight,
  AlertTriangle,
  Microscope,
  Target,
  Workflow,
  Lightbulb,
  Layers,
  Sparkles,
  Bot,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { useClinicalAnalysis } from "@/lib/hooks/use-api";

const SEVERITY_COLORS: Record<string, string> = {
  critical: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
  high: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200",
  moderate:
    "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200",
  low: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
};

const CONFIDENCE_COLORS: Record<string, string> = {
  high: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
  medium:
    "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200",
  low: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
};

const PRIORITY_INDICATORS: Record<number, string> = {
  1: "text-red-600 dark:text-red-400",
  2: "text-orange-600 dark:text-orange-400",
  3: "text-amber-600 dark:text-amber-400",
};

export default function ClinicalAnalysisPage() {
  const params = useParams();
  const sessionId = params.id as string;
  const { data: analysis, isLoading, error } = useClinicalAnalysis(sessionId);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-24" />
        <Skeleton className="h-48" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-4">
        <Link
          href={`/dashboard/report/${sessionId}`}
          className="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline"
        >
          <ArrowLeft className="h-4 w-4" /> Back to Report
        </Link>
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Clinical Analysis Unavailable</AlertTitle>
          <AlertDescription>
            {error instanceof Error
              ? error.message
              : "The clinical analysis could not be loaded. The report may not have been analyzed yet."}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  if (!analysis) return null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Link
            href={`/dashboard/report/${sessionId}`}
            className="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline mb-2"
          >
            <ArrowLeft className="h-4 w-4" /> Back to Report
          </Link>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Microscope className="h-6 w-6 text-purple-600" />
              Clinical Analysis
            </h1>
            <Badge
              variant="outline"
              className="flex items-center gap-1 text-xs"
            >
              {analysis.analysis_source === "llm" ? (
                <>
                  <Sparkles className="h-3 w-3" />
                  AI-Powered
                  {analysis.model_used ? ` (${analysis.model_used})` : ""}
                </>
              ) : (
                <>
                  <Bot className="h-3 w-3" />
                  Template Analysis
                </>
              )}
            </Badge>
          </div>
        </div>
      </div>

      {/* Medical Disclaimer */}
      <Alert className="border-amber-200 bg-amber-50 dark:bg-amber-950/30 dark:border-amber-800">
        <AlertTriangle className="h-4 w-4 text-amber-600" />
        <AlertTitle className="text-amber-800 dark:text-amber-200">
          Important Notice
        </AlertTitle>
        <AlertDescription className="text-amber-700 dark:text-amber-300 text-sm">
          This analysis identifies patterns and associations in frequency-based
          scan data. It does NOT constitute medical diagnosis or treatment
          advice. Always consult a qualified healthcare professional.
        </AlertDescription>
      </Alert>

      {/* Systemic Analysis — Main narrative */}
      {analysis.systemic_analysis && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Workflow className="h-5 w-5 text-purple-600" />
              Systemic Analysis
            </CardTitle>
            <CardDescription>
              AI-generated narrative identifying cascading patterns across organ
              systems
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="prose prose-sm dark:prose-invert max-w-none">
              {analysis.systemic_analysis.split("\n\n").map((paragraph, i) => (
                <p key={i} className="text-gray-700 dark:text-gray-300 mb-3">
                  {paragraph}
                </p>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Root Systems & Cascade Chains */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Root Systems */}
        {analysis.root_systems.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Target className="h-5 w-5 text-red-600" />
                Root Systems
              </CardTitle>
              <CardDescription>
                Organ systems identified as potential primary drivers
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {analysis.root_systems.map((root, i) => (
                <div
                  key={i}
                  className="rounded-lg border p-4 space-y-3 dark:border-gray-700"
                >
                  <div className="flex items-center justify-between">
                    <h3 className="font-semibold text-base">
                      {root.organ_system}
                    </h3>
                    <Badge
                      className={
                        CONFIDENCE_COLORS[root.confidence] || CONFIDENCE_COLORS.medium
                      }
                    >
                      {root.confidence} confidence
                    </Badge>
                  </div>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {root.reasoning}
                  </p>
                  {root.downstream_effects.length > 0 && (
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
                        Downstream:
                      </span>
                      {root.downstream_effects.map((effect, j) => (
                        <span key={j} className="inline-flex items-center gap-1">
                          {j > 0 && (
                            <ArrowRight className="h-3 w-3 text-gray-400" />
                          )}
                          <Badge variant="outline" className="text-xs">
                            {effect}
                          </Badge>
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>
        )}

        {/* Cascade Chains */}
        {analysis.cascade_chains.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Workflow className="h-5 w-5 text-blue-600" />
                Cascade Chains
              </CardTitle>
              <CardDescription>
                Organ-to-organ effect pathways supported by knowledge graph data
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {analysis.cascade_chains.map((cascade, i) => (
                <div
                  key={i}
                  className="rounded-lg border p-4 space-y-3 dark:border-gray-700"
                >
                  {/* Chain visualization */}
                  <div className="flex items-center gap-2 flex-wrap">
                    {cascade.chain.map((step, j) => (
                      <span key={j} className="inline-flex items-center gap-2">
                        {j > 0 && (
                          <ArrowRight className="h-4 w-4 text-blue-500" />
                        )}
                        <Badge
                          variant="secondary"
                          className="text-sm font-medium"
                        >
                          {step}
                        </Badge>
                      </span>
                    ))}
                  </div>

                  {/* Mechanism */}
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {cascade.mechanism}
                  </p>

                  {/* Supporting pathways */}
                  {cascade.supporting_pathways.length > 0 && (
                    <div>
                      <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
                        Supporting pathways:
                      </span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {cascade.supporting_pathways.map((pathway, j) => (
                          <Badge
                            key={j}
                            variant="outline"
                            className="text-xs bg-blue-50 dark:bg-blue-950/30"
                          >
                            {pathway}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Key conditions */}
                  {cascade.key_conditions.length > 0 && (
                    <div>
                      <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
                        Key conditions:
                      </span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {cascade.key_conditions.map((cond, j) => (
                          <Badge
                            key={j}
                            variant="outline"
                            className="text-xs"
                          >
                            {cond}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>
        )}
      </div>

      {/* Key Patterns */}
      {analysis.key_patterns.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Layers className="h-5 w-5 text-indigo-600" />
              Key Patterns
            </CardTitle>
            <CardDescription>
              Condition groups sharing biological pathways — suggesting common
              mechanisms
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {analysis.key_patterns.map((pattern, i) => (
                <div
                  key={i}
                  className="rounded-lg border p-4 space-y-3 dark:border-gray-700"
                >
                  <div className="flex items-center justify-between">
                    <h3 className="font-semibold text-sm">
                      {pattern.pattern_name}
                    </h3>
                    <Badge
                      className={
                        SEVERITY_COLORS[pattern.severity] ||
                        SEVERITY_COLORS.moderate
                      }
                    >
                      {pattern.severity}
                    </Badge>
                  </div>

                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {pattern.clinical_significance}
                  </p>

                  {/* Conditions */}
                  <div className="flex flex-wrap gap-1">
                    {pattern.conditions_involved.map((cond, j) => (
                      <Badge key={j} variant="outline" className="text-xs">
                        {cond}
                      </Badge>
                    ))}
                  </div>

                  {/* Shared pathways */}
                  {pattern.shared_pathways.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      <span className="text-xs font-medium text-gray-500 dark:text-gray-400 mr-1">
                        Pathways:
                      </span>
                      {pattern.shared_pathways.map((pw, j) => (
                        <Badge
                          key={j}
                          variant="outline"
                          className="text-xs bg-indigo-50 dark:bg-indigo-950/30 text-indigo-700 dark:text-indigo-300"
                        >
                          {pw}
                        </Badge>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Actionable Insights */}
      {analysis.actionable_insights.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Lightbulb className="h-5 w-5 text-yellow-600" />
              Actionable Insights
            </CardTitle>
            <CardDescription>
              Prioritized focus areas based on knowledge graph evidence
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {analysis.actionable_insights.map((insight, i) => (
                <div
                  key={i}
                  className="flex gap-4 rounded-lg border p-4 dark:border-gray-700"
                >
                  {/* Priority number */}
                  <div
                    className={`flex-shrink-0 flex items-center justify-center w-10 h-10 rounded-full border-2 font-bold text-lg ${
                      PRIORITY_INDICATORS[insight.priority] ||
                      "text-gray-600 dark:text-gray-400"
                    } ${
                      insight.priority === 1
                        ? "border-red-300 dark:border-red-700 bg-red-50 dark:bg-red-950/30"
                        : insight.priority === 2
                          ? "border-orange-300 dark:border-orange-700 bg-orange-50 dark:bg-orange-950/30"
                          : "border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-950/30"
                    }`}
                  >
                    {insight.priority}
                  </div>

                  <div className="flex-1 space-y-1">
                    <h3 className="font-semibold">{insight.focus_area}</h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      {insight.reasoning}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-500">
                      Supported by: {insight.supported_by}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Footer Disclaimer */}
      <Separator />
      <div className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
        <p>{analysis.disclaimer}</p>
      </div>
    </div>
  );
}
