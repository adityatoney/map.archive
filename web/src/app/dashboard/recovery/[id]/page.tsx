"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Heart,
  AlertTriangle,
  CheckCircle,
  Clock,
  Stethoscope,
  Apple,
  Dumbbell,
  Eye,
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
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { useRecoveryPlan } from "@/lib/hooks/use-api";

const CATEGORY_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  specialist_referral: Stethoscope,
  nutritional: Apple,
  lifestyle: Dumbbell,
  monitoring: Eye,
};

const PRIORITY_COLORS: Record<string, string> = {
  immediate: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
  short_term: "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200",
  ongoing: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
};

const TIER_COLORS: Record<string, string> = {
  critical: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
  high: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200",
  moderate: "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200",
  low: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
};

export default function RecoveryPage() {
  const params = useParams();
  const sessionId = params.id as string;
  const { data: plan, isLoading, error } = useRecoveryPlan(sessionId);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-32" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (error || !plan) {
    return (
      <div className="max-w-2xl mx-auto text-center py-12">
        <Heart className="h-16 w-16 mx-auto mb-4 text-gray-300" />
        <h2 className="text-xl font-semibold text-gray-600 mb-2">
          Recovery Plan Not Available
        </h2>
        <p className="text-gray-400 mb-4">
          Run analysis on this session first to generate a recovery plan.
        </p>
        <Button asChild>
          <Link href={`/dashboard/report/${sessionId}`}>
            Go to Report View
          </Link>
        </Button>
      </div>
    );
  }

  const interventions = (plan.recommended_interventions as Record<string, unknown>[]) || [];
  const lifestyle = (plan.lifestyle_recommendations as Record<string, unknown>[]) || [];
  const nutritional = (plan.nutritional_recommendations as Record<string, unknown>[]) || [];
  const priorities = (plan.priority_conditions as Record<string, unknown>[]) || [];
  const monitoring = (plan.monitoring_plan as Record<string, unknown>) || {};

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <Button variant="ghost" size="sm" asChild className="mb-2">
          <Link href={`/dashboard/report/${sessionId}`}>
            <ArrowLeft className="h-4 w-4 mr-1" /> Back to Report
          </Link>
        </Button>
        <h1 className="text-2xl font-bold">Recovery Plan</h1>
        <p className="text-gray-500">
          Generated{" "}
          {plan.generated_at
            ? new Date(plan.generated_at).toLocaleDateString()
            : "N/A"}
        </p>
      </div>

      {/* IMPORTANT: Inline medical disclaimer */}
      <Alert className="border-amber-300 bg-amber-50 dark:bg-amber-950/30">
        <AlertTriangle className="h-5 w-5 text-amber-600" />
        <AlertTitle className="text-amber-800 dark:text-amber-200">
          Important Medical Disclaimer
        </AlertTitle>
        <AlertDescription className="text-amber-700 dark:text-amber-300 text-sm">
          {plan.disclaimer}
        </AlertDescription>
      </Alert>

      {/* Summary */}
      {plan.summary && (
        <Card>
          <CardHeader>
            <CardTitle>Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm leading-relaxed text-gray-700 dark:text-gray-300">
              {plan.summary}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Priority conditions */}
      {priorities.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Priority Conditions</CardTitle>
            <CardDescription>
              Top conditions ranked by risk score + knowledge graph connectivity
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {priorities.map((cond, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between p-3 border rounded-md"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-lg font-bold text-gray-300 w-6">
                      {String(cond.rank)}
                    </span>
                    <div>
                      <p className="font-medium text-sm">
                        {String(cond.condition_name)}
                        {Number(cond.occurrence_count) > 1 && (
                          <span className="text-xs text-gray-400 ml-1">
                            ({String(cond.occurrence_count)} locations)
                          </span>
                        )}
                      </p>
                      <p className="text-xs text-gray-500">
                        {String(cond.organ_system)}
                        {cond.anatomical_location
                          ? ` | ${String(cond.anatomical_location)}`
                          : ""}
                      </p>
                      {cond.reasoning ? (
                        <p className="text-xs text-blue-600 dark:text-blue-400 mt-0.5">
                          {String(cond.reasoning)}
                        </p>
                      ) : null}
                    </div>
                  </div>
                  <div className="text-right">
                    <Badge
                      className={
                        TIER_COLORS[String(cond.risk_tier)] || ""
                      }
                      variant="secondary"
                    >
                      {String(cond.risk_tier)}
                    </Badge>
                    <p className="text-xs text-gray-500 mt-1">
                      Score: {String(cond.score)}
                    </p>
                    {cond.kg_connected ? (
                      <p className="text-[10px] text-purple-500 dark:text-purple-400">
                        KG-enriched
                      </p>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Interventions */}
      {interventions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Recommended Interventions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {interventions.map((intv, i) => {
                const Icon =
                  CATEGORY_ICONS[String(intv.category)] || CheckCircle;
                return (
                  <div key={i} className="p-3 border rounded-md">
                    <div className="flex items-start gap-3">
                      <Icon className="h-5 w-5 mt-0.5 text-blue-600 flex-shrink-0" />
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <p className="font-medium text-sm">
                            {String(intv.intervention)}
                          </p>
                          <Badge
                            className={
                              PRIORITY_COLORS[String(intv.priority)] || ""
                            }
                            variant="secondary"
                          >
                            {String(intv.priority)}
                          </Badge>
                        </div>
                        <p className="text-xs text-gray-500">
                          {String(intv.reasoning)}
                        </p>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Lifestyle & Nutritional side by side */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Dumbbell className="h-5 w-5" /> Lifestyle
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-3">
              {lifestyle.map((rec, i) => (
                <li key={i} className="text-sm">
                  <p className="font-medium">
                    {String(rec.recommendation)}
                  </p>
                  <p className="text-xs text-gray-500">
                    {String(rec.relevance)}
                  </p>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Apple className="h-5 w-5" /> Nutritional
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-3">
              {nutritional.map((rec, i) => (
                <li key={i} className="text-sm">
                  <p className="font-medium">
                    {String(rec.recommendation)}
                  </p>
                  <p className="text-xs text-gray-500">
                    {String(rec.relevance)}
                  </p>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>

      {/* Monitoring plan */}
      {monitoring && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5" /> Monitoring Plan
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm space-y-2">
            <p>
              <strong>Recommended rescan interval:</strong>{" "}
              {String(monitoring.recommended_rescan_interval || "N/A")}
            </p>
            {(monitoring.watch_conditions as string[])?.length > 0 && (
              <div>
                <strong>Watch conditions:</strong>
                <ul className="list-disc list-inside ml-2 text-gray-600 dark:text-gray-400">
                  {(monitoring.watch_conditions as string[]).map(
                    (c: string, i: number) => (
                      <li key={i}>{c}</li>
                    )
                  )}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Print-friendly note */}
      <div className="text-center text-xs text-gray-400 print:block">
        <Separator className="mb-4" />
        <p>
          This recovery plan was generated by Medical Analytics Platform and
          should be reviewed with a qualified healthcare professional.
        </p>
      </div>
    </div>
  );
}
