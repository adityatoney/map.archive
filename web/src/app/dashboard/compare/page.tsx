"use client";

import { useState } from "react";
import {
  GitCompare,
  ArrowUp,
  ArrowDown,
  Minus,
  Plus,
  X,
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { usePatientStore } from "@/lib/stores/patient-store";
import { usePatientHistory, useCompareSessions } from "@/lib/hooks/use-api";

const STATUS_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  improved: ArrowDown,
  worsened: ArrowUp,
  stable: Minus,
  new: Plus,
  resolved: X,
};

const STATUS_COLORS: Record<string, string> = {
  improved: "text-green-600",
  worsened: "text-red-600",
  stable: "text-gray-400",
  new: "text-blue-600",
  resolved: "text-gray-400",
};

export default function ComparePage() {
  const { selectedPatientId } = usePatientStore();
  const { data: history } = usePatientHistory(selectedPatientId);
  const compare = useCompareSessions();

  const [session1, setSession1] = useState("");
  const [session2, setSession2] = useState("");

  const sessions = history?.sessions || [];

  const handleCompare = () => {
    if (session1 && session2) {
      compare.mutate({ sessionId1: session1, sessionId2: session2 });
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Session Comparison</h1>
        <p className="text-gray-500">
          Compare two scan sessions to track changes
        </p>
      </div>

      {/* Session selectors */}
      <Card>
        <CardHeader>
          <CardTitle>Select Sessions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row items-end gap-4">
            <div className="flex-1 w-full">
              <label className="text-sm font-medium mb-1 block">
                Session 1 (Earlier)
              </label>
              <Select value={session1} onValueChange={setSession1}>
                <SelectTrigger>
                  <SelectValue placeholder="Select session..." />
                </SelectTrigger>
                <SelectContent>
                  {sessions.map((s) => (
                    <SelectItem key={s.id} value={s.id}>
                      {new Date(s.scan_date).toLocaleDateString()} (
                      {s.entry_count} conditions)
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <GitCompare className="h-6 w-6 text-gray-400 flex-shrink-0 hidden sm:block" />

            <div className="flex-1 w-full">
              <label className="text-sm font-medium mb-1 block">
                Session 2 (Later)
              </label>
              <Select value={session2} onValueChange={setSession2}>
                <SelectTrigger>
                  <SelectValue placeholder="Select session..." />
                </SelectTrigger>
                <SelectContent>
                  {sessions.map((s) => (
                    <SelectItem key={s.id} value={s.id}>
                      {new Date(s.scan_date).toLocaleDateString()} (
                      {s.entry_count} conditions)
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <Button
              onClick={handleCompare}
              disabled={!session1 || !session2 || compare.isPending}
            >
              Compare
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Results */}
      {compare.data && (
        <>
          {/* Summary badges */}
          <div className="flex flex-wrap gap-3">
            <Badge variant="secondary" className="bg-green-100 text-green-800">
              {
                compare.data.deltas.filter((d) => d.status === "improved")
                  .length
              }{" "}
              Improved
            </Badge>
            <Badge variant="secondary" className="bg-red-100 text-red-800">
              {
                compare.data.deltas.filter((d) => d.status === "worsened")
                  .length
              }{" "}
              Worsened
            </Badge>
            <Badge variant="secondary">
              {
                compare.data.deltas.filter((d) => d.status === "stable")
                  .length
              }{" "}
              Stable
            </Badge>
            {compare.data.new_conditions.length > 0 && (
              <Badge
                variant="secondary"
                className="bg-blue-100 text-blue-800"
              >
                {compare.data.new_conditions.length} New
              </Badge>
            )}
            {compare.data.resolved_conditions.length > 0 && (
              <Badge variant="secondary">
                {compare.data.resolved_conditions.length} Resolved
              </Badge>
            )}
          </div>

          {/* Delta table */}
          <Card>
            <CardHeader>
              <CardTitle>Condition Deltas</CardTitle>
              <CardDescription>
                Score changes between{" "}
                {new Date(compare.data.session_1_date).toLocaleDateString()}{" "}
                and{" "}
                {new Date(compare.data.session_2_date).toLocaleDateString()}
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Condition</TableHead>
                    <TableHead>Organ System</TableHead>
                    <TableHead className="text-right">Score 1</TableHead>
                    <TableHead className="text-right">Score 2</TableHead>
                    <TableHead className="text-right">Delta</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {compare.data.deltas.map((d) => {
                    const Icon = STATUS_ICONS[d.status] || Minus;
                    const color = STATUS_COLORS[d.status] || "";
                    return (
                      <TableRow key={d.condition_name}>
                        <TableCell className="font-medium">
                          {d.condition_name}
                        </TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {d.organ_system || "—"}
                        </TableCell>
                        <TableCell className="text-right font-mono text-sm">
                          {d.score_1?.toFixed(3) ?? "—"}
                        </TableCell>
                        <TableCell className="text-right font-mono text-sm">
                          {d.score_2?.toFixed(3) ?? "—"}
                        </TableCell>
                        <TableCell className={`text-right font-mono text-sm ${color}`}>
                          {d.delta != null
                            ? `${d.delta > 0 ? "+" : ""}${d.delta.toFixed(4)}`
                            : "—"}
                        </TableCell>
                        <TableCell>
                          <div className={`flex items-center gap-1 ${color}`}>
                            <Icon className="h-4 w-4" />
                            <span className="text-xs capitalize">
                              {d.status}
                            </span>
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </>
      )}

      {!compare.data && !compare.isPending && (
        <div className="text-center py-12 text-gray-400">
          <GitCompare className="h-16 w-16 mx-auto mb-4 opacity-30" />
          <p>Select two sessions above and click Compare</p>
        </div>
      )}
    </div>
  );
}
