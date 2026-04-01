"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  Minus,
  AlertTriangle,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

export default function TrendsPage() {
  const params = useParams();
  void params.id; // patientId — used in Phase 5 for trend data fetching

  // Phase 1: Placeholder — real trend data requires multiple sessions analyzed
  const trendSummary = [
    { label: "Improving", count: 4, color: "text-green-600", icon: TrendingDown },
    { label: "Stable", count: 6, color: "text-blue-600", icon: Minus },
    { label: "Worsening", count: 3, color: "text-orange-600", icon: TrendingUp },
    { label: "Critical", count: 1, color: "text-red-600", icon: AlertTriangle },
  ];

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

      {/* Trend summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {trendSummary.map((item) => {
          const Icon = item.icon;
          return (
            <Card key={item.label}>
              <CardContent className="pt-6 text-center">
                <Icon className={`h-8 w-8 mx-auto mb-2 ${item.color}`} />
                <p className="text-2xl font-bold">{item.count}</p>
                <p className="text-sm text-gray-500">{item.label}</p>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Sparkline grid placeholder */}
      <Card>
        <CardHeader>
          <CardTitle>Condition Sparklines</CardTitle>
          <CardDescription>
            Score over time for each condition across all sessions
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <div
                key={i}
                className="p-4 border rounded-md bg-gray-50 dark:bg-gray-800/50"
              >
                <Skeleton className="h-4 w-32 mb-2" />
                <Skeleton className="h-16 w-full" />
              </div>
            ))}
          </div>
          <p className="text-sm text-gray-400 mt-4 text-center">
            Recharts sparkline grid — coming in Phase 5. Requires multiple
            analyzed sessions.
          </p>
        </CardContent>
      </Card>

      {/* Session comparison slider placeholder */}
      <Card>
        <CardHeader>
          <CardTitle>Session Comparison</CardTitle>
          <CardDescription>
            Select two sessions to compare side by side
          </CardDescription>
        </CardHeader>
        <CardContent className="flex items-center justify-center h-32 text-gray-400">
          <p className="text-sm">
            Session comparison slider — coming in Phase 5
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
