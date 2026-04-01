"use client";

import { useEffect } from "react";
import Link from "next/link";
import {
  Activity,
  AlertTriangle,
  Download,
  FileUp,
  GitCompare,
  Heart,
  TrendingUp,
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
import { usePatientStore } from "@/lib/stores/patient-store";
import { usePatientHistory } from "@/lib/hooks/use-api";
import apiClient from "@/lib/api-client";

function MetricCard({
  title,
  value,
  subtitle,
  icon: Icon,
  variant = "default",
}: {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ComponentType<{ className?: string }>;
  variant?: "default" | "success" | "warning" | "danger";
}) {
  const colors = {
    default: "text-blue-600",
    success: "text-green-600",
    warning: "text-amber-600",
    danger: "text-red-600",
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-gray-500">
          {title}
        </CardTitle>
        <Icon className={`h-5 w-5 ${colors[variant]}`} />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {subtitle && (
          <p className="text-xs text-gray-500 mt-1">{subtitle}</p>
        )}
      </CardContent>
    </Card>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function RiskTierBadge({ tier }: { tier: string }) {
  const colors: Record<string, string> = {
    low: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
    moderate:
      "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200",
    high: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200",
    critical: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
  };
  return (
    <Badge className={colors[tier] || colors.low} variant="secondary">
      {tier}
    </Badge>
  );
}

export default function DashboardPage() {
  const { selectedPatientId, patients, setLatestSessionId } = usePatientStore();
  const { data: history, isLoading } = usePatientHistory(selectedPatientId);

  const selectedPatient = patients.find((p) => p.id === selectedPatientId);

  // Keep sidebar nav in sync with the latest session
  const latestId = history?.sessions[0]?.id || null;
  useEffect(() => {
    setLatestSessionId(latestId);
  }, [latestId, setLatestSessionId]);

  if (!selectedPatientId) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] text-center">
        <Activity className="h-16 w-16 text-gray-300 mb-4" />
        <h2 className="text-xl font-semibold text-gray-600">
          Select a Patient
        </h2>
        <p className="text-gray-400 mt-2">
          Choose a patient from the dropdown above to view their dashboard
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
        <Skeleton className="h-64" />
      </div>
    );
  }

  const latestSession = history?.sessions[0];
  const totalSessions = history?.total_sessions || 0;

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold">
          {selectedPatient?.first_name} {selectedPatient?.last_name}
        </h1>
        <p className="text-gray-500">
          Age: {selectedPatient?.age} | Blood Group:{" "}
          {selectedPatient?.blood_group || "N/A"} | Scans: {totalSessions}
        </p>
      </div>

      {/* Metric cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Scans"
          value={totalSessions}
          subtitle="Across all sessions"
          icon={Activity}
        />
        <MetricCard
          title="Latest Scan"
          value={
            latestSession
              ? new Date(latestSession.scan_date).toLocaleDateString()
              : "N/A"
          }
          subtitle={
            latestSession
              ? `${latestSession.entry_count} conditions`
              : undefined
          }
          icon={FileUp}
        />
        <MetricCard
          title="Conditions Flagged"
          value={latestSession?.entry_count || 0}
          subtitle="In latest scan"
          icon={AlertTriangle}
          variant="warning"
        />
        <MetricCard
          title="Analysis Status"
          value={latestSession?.analysis_status || "N/A"}
          icon={TrendingUp}
          variant={
            latestSession?.analysis_status === "completed"
              ? "success"
              : "default"
          }
        />
      </div>

      {/* Body map placeholder + recent sessions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Body map placeholder */}
        <Card>
          <CardHeader>
            <CardTitle>Organ System Risk Map</CardTitle>
            <CardDescription>
              Body silhouette with risk overlays (coming in Phase 5)
            </CardDescription>
          </CardHeader>
          <CardContent className="flex items-center justify-center h-64 bg-gray-50 dark:bg-gray-800/50 rounded-md">
            <div className="text-center text-gray-400">
              <Activity className="h-16 w-16 mx-auto mb-2 opacity-30" />
              <p className="text-sm">Interactive body map coming soon</p>
            </div>
          </CardContent>
        </Card>

        {/* Recent sessions */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Scan Sessions</CardTitle>
            <CardDescription>
              Click a session to view detailed report
            </CardDescription>
          </CardHeader>
          <CardContent>
            {history?.sessions.length === 0 ? (
              <p className="text-gray-400 text-sm">No sessions yet</p>
            ) : (
              <div className="space-y-3">
                {history?.sessions.slice(0, 5).map((s) => (
                  <div
                    key={s.id}
                    className="flex items-center justify-between p-3 rounded-md border hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                  >
                    <Link
                      href={`/dashboard/report/${s.id}`}
                      className="flex-1 min-w-0"
                    >
                      <p className="font-medium text-sm">
                        {new Date(s.scan_date).toLocaleDateString()}{" "}
                        <span className="text-gray-400 font-normal">
                          ({s.report_type.toUpperCase()})
                        </span>
                      </p>
                      <p className="text-xs text-gray-500">
                        {s.entry_count} conditions
                      </p>
                    </Link>
                    <div className="flex items-center gap-2 ml-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          apiClient.downloadReport(s.id).catch((err) =>
                            console.error("Download failed:", err)
                          );
                        }}
                        className="p-1.5 rounded-md text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:text-gray-300 dark:hover:bg-gray-700 transition-colors"
                        title="Download original report"
                      >
                        <Download className="h-4 w-4" />
                      </button>
                      <Badge
                        variant={
                          s.analysis_status === "completed"
                            ? "default"
                            : "secondary"
                        }
                      >
                        {s.analysis_status}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Quick actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3">
          <Button asChild>
            <Link href="/dashboard/upload">
              <FileUp className="h-4 w-4 mr-2" />
              Upload New Scan
            </Link>
          </Button>
          {latestSession && (
            <>
              <Button variant="outline" asChild>
                <Link href={`/dashboard/recovery/${latestSession.id}`}>
                  <Heart className="h-4 w-4 mr-2" />
                  View Recovery Plan
                </Link>
              </Button>
              <Button variant="outline" asChild>
                <Link href="/dashboard/compare">
                  <GitCompare className="h-4 w-4 mr-2" />
                  Compare Sessions
                </Link>
              </Button>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
