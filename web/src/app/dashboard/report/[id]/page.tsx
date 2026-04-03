"use client";

import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useMemo, useState } from "react";
import {
  ArrowLeft,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Brain,
  ChevronDown,
  ChevronRight,
  Filter,
  Heart,
  Loader2,
  Microscope,
  RefreshCw,
  Search,
  Trash2,
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
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { Progress } from "@/components/ui/progress";
import { useReport, useAnalyzeReport, useDeleteReport, useInsights } from "@/lib/hooks/use-api";
import type { ScanEntry } from "@/lib/api-client";
import { ClusterScatter } from "@/components/charts/cluster-scatter";

// --------------- Constants ---------------

const RISK_TIERS = ["critical", "high", "moderate", "low"] as const;
type RiskTier = (typeof RISK_TIERS)[number];

const RISK_DOT_COLORS: Record<string, string> = {
  all: "bg-gray-800 dark:bg-gray-200",
  critical: "bg-red-500",
  high: "bg-orange-500",
  moderate: "bg-amber-500",
  low: "bg-green-500",
};

const RISK_BADGE_COLORS: Record<string, string> = {
  low: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  moderate:
    "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200",
  high: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200",
  critical: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
};

type SortField =
  | "condition_name"
  | "anatomical_location"
  | "organ_system"
  | "score"
  | "risk_tier";
type SortDir = "asc" | "desc";

const RISK_ORDER: Record<string, number> = {
  critical: 4,
  high: 3,
  moderate: 2,
  low: 1,
};

// --------------- Sub-components ---------------

function RiskBadge({ tier }: { tier: string | null | undefined }) {
  if (!tier) return null;
  return (
    <Badge className={RISK_BADGE_COLORS[tier] || ""} variant="secondary">
      {tier}
    </Badge>
  );
}

function ScoreBar({ score }: { score: number }) {
  // Inverted: lower score = higher risk, so fill bar inversely
  const riskPercentage = (1 - score) * 100;
  const color =
    score < 0.1
      ? "bg-red-500"
      : score < 0.2
      ? "bg-orange-500"
      : score < 0.4
      ? "bg-amber-500"
      : "bg-green-500";

  return (
    <div className="flex items-center gap-2 min-w-[120px]">
      <div className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${color}`}
          style={{ width: `${riskPercentage}%` }}
        />
      </div>
      <span className="text-xs font-mono w-10 text-right">
        {score.toFixed(3)}
      </span>
    </div>
  );
}

/** Pill-shaped filter tab with dot + count. */
function FilterPill({
  label,
  count,
  dotColor,
  active,
  onClick,
}: {
  label: string;
  count: number;
  dotColor: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`
        inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-medium
        transition-colors whitespace-nowrap
        ${
          active
            ? "bg-gray-900 text-white dark:bg-white dark:text-gray-900"
            : "bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
        }
      `}
    >
      <span
        className={`h-2 w-2 rounded-full ${
          active ? "bg-white dark:bg-gray-900" : dotColor
        }`}
      />
      {label}
      <span
        className={`ml-0.5 text-xs ${
          active
            ? "text-gray-300 dark:text-gray-600"
            : "text-gray-400 dark:text-gray-500"
        }`}
      >
        {count}
      </span>
    </button>
  );
}

/** Sortable + filterable column header. */
function SortableHead({
  label,
  field,
  currentSort,
  currentDir,
  onSort,
  filterIcon,
}: {
  label: string;
  field: SortField;
  currentSort: SortField;
  currentDir: SortDir;
  onSort: (f: SortField) => void;
  filterIcon?: React.ReactNode;
}) {
  const isActive = currentSort === field;
  return (
    <TableHead className="bg-gray-50 dark:bg-gray-800/60 text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 border-b-2 border-gray-200 dark:border-gray-700">
      <div className="flex items-center gap-1">
        {filterIcon}
        <button
          className="flex items-center gap-1 hover:text-foreground transition-colors"
          onClick={() => onSort(field)}
        >
          {label}
          {isActive ? (
            currentDir === "asc" ? (
              <ArrowUp className="h-3 w-3" />
            ) : (
              <ArrowDown className="h-3 w-3" />
            )
          ) : (
            <ArrowUpDown className="h-3 w-3 opacity-40" />
          )}
        </button>
      </div>
    </TableHead>
  );
}

/** Checkbox-style filter item row (inspired by Sevarthi Filter Status). */
function FilterCheckboxItem({
  label,
  count,
  checked,
  onToggle,
}: {
  label: string;
  count: number;
  checked: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      onClick={(e) => {
        e.preventDefault();
        onToggle();
      }}
      className="flex items-center gap-3 w-full px-3 py-2.5 text-sm hover:bg-accent rounded-sm transition-colors text-left"
    >
      {/* Checkbox */}
      <div
        className={`h-4.5 w-4.5 rounded border-2 flex items-center justify-center shrink-0 transition-colors ${
          checked
            ? "bg-blue-600 border-blue-600"
            : "border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800"
        }`}
        style={{ height: 18, width: 18 }}
      >
        {checked && (
          <svg
            className="h-3 w-3 text-white"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={3}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M5 13l4 4L19 7"
            />
          </svg>
        )}
      </div>
      <span className="flex-1 truncate">{label}</span>
      <span className="text-xs text-muted-foreground tabular-nums">{count}</span>
    </button>
  );
}

/** Dropdown filter for a set of string values with checkboxes + Select All. */
function ColumnFilter({
  title,
  options,
  selected,
  onToggle,
  onClear,
  onSelectAll,
}: {
  title: string;
  options: { value: string; count: number }[];
  selected: Set<string>;
  onToggle: (value: string) => void;
  onClear: () => void;
  onSelectAll: () => void;
}) {
  const hasFilters = selected.size > 0;
  const allSelected = selected.size === options.length;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button className="relative p-0.5 rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors">
          <Filter
            className={`h-3.5 w-3.5 ${
              hasFilters
                ? "text-blue-600 dark:text-blue-400"
                : "opacity-40"
            }`}
          />
          {hasFilters && (
            <span className="absolute -top-1 -right-1 h-2 w-2 rounded-full bg-blue-500" />
          )}
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        align="start"
        className="w-64"
        onCloseAutoFocus={(e) => e.preventDefault()}
      >
        <DropdownMenuLabel className="flex items-center justify-between text-xs uppercase tracking-wider text-muted-foreground font-semibold">
          Filter {title}
          {hasFilters && (
            <button
              onClick={(e) => {
                e.preventDefault();
                onClear();
              }}
              className="text-xs text-blue-600 dark:text-blue-400 hover:underline font-normal normal-case tracking-normal"
            >
              Clear
            </button>
          )}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />

        <div className="max-h-64 overflow-y-auto py-1">
          {options.map((opt) => (
            <FilterCheckboxItem
              key={opt.value}
              label={opt.value}
              count={opt.count}
              checked={selected.has(opt.value)}
              onToggle={() => onToggle(opt.value)}
            />
          ))}
        </div>

        <DropdownMenuSeparator />
        <button
          onClick={(e) => {
            e.preventDefault();
            if (allSelected) {
              onClear();
            } else {
              onSelectAll();
            }
          }}
          className="w-full py-2 text-sm text-center font-medium text-muted-foreground hover:text-foreground transition-colors"
        >
          {allSelected ? "Deselect All" : "Select All"}
        </button>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

// --------------- Organ System Accordion ---------------

function OrganSystemAccordion({
  organGroups,
}: {
  organGroups: Record<string, ScanEntry[]>;
}) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  // Sort organ systems alphabetically, conditions within each group alphabetically
  const sortedOrgans = useMemo(() => {
    return Object.entries(organGroups)
      .map(([organ, entries]) => {
        const avg = entries.reduce((s, e) => s + e.score, 0) / entries.length;
        const sorted = [...entries].sort((a, b) =>
          a.condition_name.localeCompare(b.condition_name)
        );
        const maxRisk = [...entries].sort(
          (a, b) =>
            (RISK_ORDER[b.risk_tier || ""] || 0) -
            (RISK_ORDER[a.risk_tier || ""] || 0)
        )[0]?.risk_tier || null;
        return { organ, entries: sorted, avg, maxRisk };
      })
      .sort((a, b) => a.organ.localeCompare(b.organ));
  }, [organGroups]);

  const totalConditions = useMemo(
    () => sortedOrgans.reduce((s, o) => s + o.entries.length, 0),
    [sortedOrgans]
  );

  function toggle(organ: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(organ)) next.delete(organ);
      else next.add(organ);
      return next;
    });
  }

  function expandAll() {
    setExpanded(new Set(sortedOrgans.map((o) => o.organ)));
  }

  function collapseAll() {
    setExpanded(new Set());
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <CardTitle>Score Distribution by Organ System</CardTitle>
            <Badge variant="secondary" className="text-xs font-normal">
              {totalConditions}
            </Badge>
          </div>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="sm"
              className="text-xs h-7 px-2"
              onClick={expandAll}
            >
              Expand all
            </Button>
            <span className="text-muted-foreground text-xs">|</span>
            <Button
              variant="ghost"
              size="sm"
              className="text-xs h-7 px-2"
              onClick={collapseAll}
            >
              Collapse all
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="rounded-lg border divide-y">
          {sortedOrgans.map(({ organ, entries, avg, maxRisk }) => {
            const isOpen = expanded.has(organ);
            const barColor =
              avg >= 0.75
                ? "bg-red-500"
                : avg >= 0.5
                ? "bg-orange-500"
                : avg >= 0.25
                ? "bg-amber-500"
                : "bg-green-500";

            return (
              <div key={organ}>
                {/* Organ system header row */}
                <button
                  onClick={() => toggle(organ)}
                  className="w-full flex items-center gap-3 px-4 py-3 hover:bg-muted/50 transition-colors text-left"
                >
                  {isOpen ? (
                    <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
                  )}

                  <span className="font-medium text-sm">{organ}</span>

                  <Badge
                    variant="secondary"
                    className="text-xs font-normal shrink-0"
                  >
                    {entries.length} condition
                    {entries.length !== 1 ? "s" : ""}
                  </Badge>

                  {/* Progress bar in header */}
                  <div className="flex-1 flex items-center gap-2 ml-2">
                    <div className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden max-w-xs">
                      <div
                        className={`h-full rounded-full ${barColor}`}
                        style={{ width: `${avg * 100}%` }}
                      />
                    </div>
                    <span className="text-xs text-muted-foreground font-mono w-12 text-right shrink-0">
                      {avg.toFixed(3)}
                    </span>
                  </div>

                  {maxRisk && <RiskBadge tier={maxRisk} />}
                </button>

                {/* Expanded child conditions */}
                {isOpen && (
                  <div className="bg-muted/30">
                    {entries.map((entry, idx) => (
                      <div
                        key={entry.id}
                        className="flex items-center gap-3 pl-6 pr-4 py-2.5 hover:bg-muted/50 transition-colors"
                      >
                        {/* Tree connector lines */}
                        <div className="relative w-5 flex justify-center shrink-0">
                          <div
                            className={`absolute left-1/2 -translate-x-1/2 top-0 w-px bg-gray-300 dark:bg-gray-600 ${
                              idx === entries.length - 1 ? "h-1/2" : "h-full"
                            }`}
                          />
                          <div className="absolute left-1/2 top-1/2 -translate-y-1/2 w-2.5 h-px bg-gray-300 dark:bg-gray-600" />
                          <div className="relative z-10 h-1.5 w-1.5 rounded-full bg-gray-400 dark:bg-gray-500 mt-px" />
                        </div>

                        {/* Condition name */}
                        <span className="text-sm flex-1 min-w-0 truncate">
                          {entry.condition_name}
                          {entry.marker && (
                            <span className="ml-1 text-xs text-gray-400">
                              #{entry.marker}
                            </span>
                          )}
                        </span>

                        {/* Location */}
                        <span className="text-xs text-muted-foreground truncate max-w-[150px] hidden sm:inline">
                          {entry.anatomical_location || "\u2014"}
                        </span>

                        {/* Score bar */}
                        <div className="shrink-0">
                          <ScoreBar score={entry.score} />
                        </div>

                        {/* Risk badge */}
                        <div className="shrink-0 w-20 text-right">
                          <RiskBadge tier={entry.risk_tier} />
                        </div>

                        {/* ICD-10 */}
                        <span className="text-xs font-mono text-muted-foreground w-16 text-right shrink-0 hidden md:inline">
                          {entry.condition_icd10 || "\u2014"}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

// --------------- Main Page ---------------

export default function ReportPage() {
  const params = useParams();
  const sessionId = params.id as string;
  const {
    data: report,
    isLoading,
    error,
  } = useReport(sessionId, { poll: true });
  const analyze = useAnalyzeReport();
  const deleteReport = useDeleteReport();
  const { data: insightsData } = useInsights(
    report?.analysis_status === "completed" ? sessionId : null
  );
  const router = useRouter();
  const [confirmDelete, setConfirmDelete] = useState(false);

  // Filter state
  const [riskFilter, setRiskFilter] = useState<RiskTier | "all">("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [organFilter, setOrganFilter] = useState<Set<string>>(new Set());
  const [locationFilter, setLocationFilter] = useState<Set<string>>(new Set());

  // Sort state
  const [sortField, setSortField] = useState<SortField>("score");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  // Compute risk counts from all entries (unfiltered)
  const riskCounts = useMemo(() => {
    if (!report) return { all: 0, critical: 0, high: 0, moderate: 0, low: 0 };
    const counts: Record<string, number> = {
      all: report.entries.length,
      critical: 0,
      high: 0,
      moderate: 0,
      low: 0,
    };
    report.entries.forEach((e) => {
      const t = e.risk_tier?.toLowerCase();
      if (t && t in counts) counts[t]++;
    });
    return counts;
  }, [report]);

  // Unique organ systems + locations with counts (sorted alphabetically)
  const organOptions = useMemo(() => {
    if (!report) return [];
    const map = new Map<string, number>();
    report.entries.forEach((e) => {
      const v = e.organ_system || "Unknown";
      map.set(v, (map.get(v) || 0) + 1);
    });
    return Array.from(map.entries())
      .map(([value, count]) => ({ value, count }))
      .sort((a, b) => a.value.localeCompare(b.value));
  }, [report]);

  const locationOptions = useMemo(() => {
    if (!report) return [];
    const map = new Map<string, number>();
    report.entries.forEach((e) => {
      const v = e.anatomical_location || "Unknown";
      map.set(v, (map.get(v) || 0) + 1);
    });
    return Array.from(map.entries())
      .map(([value, count]) => ({ value, count }))
      .sort((a, b) => a.value.localeCompare(b.value));
  }, [report]);

  // Filtered + sorted entries
  const filteredEntries = useMemo(() => {
    if (!report) return [];

    let entries = [...report.entries];

    // Risk tier filter
    if (riskFilter !== "all") {
      entries = entries.filter(
        (e) => e.risk_tier?.toLowerCase() === riskFilter
      );
    }

    // Search filter (condition name, ICD-10, marker)
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      entries = entries.filter(
        (e) =>
          e.condition_name.toLowerCase().includes(q) ||
          (e.condition_icd10 &&
            e.condition_icd10.toLowerCase().includes(q)) ||
          (e.marker && e.marker.toLowerCase().includes(q)) ||
          (e.anatomical_location &&
            e.anatomical_location.toLowerCase().includes(q))
      );
    }

    // Organ system column filter
    if (organFilter.size > 0) {
      entries = entries.filter((e) =>
        organFilter.has(e.organ_system || "Unknown")
      );
    }

    // Anatomical location column filter
    if (locationFilter.size > 0) {
      entries = entries.filter((e) =>
        locationFilter.has(e.anatomical_location || "Unknown")
      );
    }

    // Sort
    entries.sort((a, b) => {
      let cmp = 0;
      switch (sortField) {
        case "condition_name":
          cmp = a.condition_name.localeCompare(b.condition_name);
          break;
        case "anatomical_location":
          cmp = (a.anatomical_location || "").localeCompare(
            b.anatomical_location || ""
          );
          break;
        case "organ_system":
          cmp = (a.organ_system || "").localeCompare(b.organ_system || "");
          break;
        case "score":
          cmp = a.score - b.score;
          break;
        case "risk_tier":
          cmp =
            (RISK_ORDER[a.risk_tier || ""] || 0) -
            (RISK_ORDER[b.risk_tier || ""] || 0);
          break;
      }
      return sortDir === "asc" ? cmp : -cmp;
    });

    return entries;
  }, [
    report,
    riskFilter,
    searchQuery,
    organFilter,
    locationFilter,
    sortField,
    sortDir,
  ]);

  // Group by organ system for distribution tab (uses all entries)
  const organGroups = useMemo(() => {
    if (!report) return {};
    const groups: Record<string, ScanEntry[]> = {};
    report.entries.forEach((e) => {
      const org = e.organ_system || "Unknown";
      if (!groups[org]) groups[org] = [];
      groups[org].push(e);
    });
    return groups;
  }, [report]);

  // Handlers
  function handleSort(field: SortField) {
    if (sortField === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDir(field === "score" || field === "risk_tier" ? "desc" : "asc");
    }
  }

  function toggleSetItem(
    setter: React.Dispatch<React.SetStateAction<Set<string>>>,
    value: string
  ) {
    setter((prev) => {
      const next = new Set(prev);
      if (next.has(value)) next.delete(value);
      else next.add(value);
      return next;
    });
  }

  function selectAll(
    setter: React.Dispatch<React.SetStateAction<Set<string>>>,
    options: { value: string }[]
  ) {
    setter(new Set(options.map((o) => o.value)));
  }

  const hasActiveFilters =
    riskFilter !== "all" ||
    searchQuery.trim() !== "" ||
    organFilter.size > 0 ||
    locationFilter.size > 0;

  function clearAllFilters() {
    setRiskFilter("all");
    setSearchQuery("");
    setOrganFilter(new Set());
    setLocationFilter(new Set());
  }

  // Loading / error states
  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="text-center py-12 text-gray-500">
        Report not found or failed to load.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Button variant="ghost" size="sm" asChild className="mb-2">
            <Link href="/dashboard">
              <ArrowLeft className="h-4 w-4 mr-1" /> Back
            </Link>
          </Button>
          <h1 className="text-2xl font-bold">Scan Report</h1>
          <p className="text-gray-500">
            {report.report_generated_at
              ? `Report: ${new Date(report.report_generated_at).toLocaleString()} | `
              : ""}
            Uploaded: {new Date(report.scan_date).toLocaleDateString()} |{" "}
            {report.report_type.toUpperCase()} | {report.entry_count} conditions
          </p>
        </div>
        <div className="flex gap-2">
          {report.analysis_status !== "completed" && (
            <Button
              onClick={() => analyze.mutate(sessionId)}
              disabled={
                analyze.isPending || report.analysis_status === "processing"
              }
            >
              {analyze.isPending ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Brain className="h-4 w-4 mr-2" />
              )}
              Run Analysis
            </Button>
          )}
          {report.analysis_status === "processing" && (
            <Button variant="outline" disabled>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Analyzing...
            </Button>
          )}
          {report.analysis_status === "completed" && (
            <>
              <Button
                variant="outline"
                onClick={() => analyze.mutate(sessionId)}
                disabled={analyze.isPending}
              >
                {analyze.isPending ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <RefreshCw className="h-4 w-4 mr-2" />
                )}
                Re-analyze
              </Button>
              <Button variant="outline" asChild>
                <Link href={`/dashboard/insights/${sessionId}`}>
                  <Brain className="h-4 w-4 mr-2" /> Insights
                </Link>
              </Button>
              <Button variant="outline" asChild>
                <Link href={`/dashboard/clinical-analysis/${sessionId}`}>
                  <Microscope className="h-4 w-4 mr-2" /> Clinical Analysis
                </Link>
              </Button>
              <Button variant="outline" asChild>
                <Link href={`/dashboard/recovery/${sessionId}`}>
                  <Heart className="h-4 w-4 mr-2" /> Recovery Plan
                </Link>
              </Button>
            </>
          )}
          <Button
            variant="ghost"
            size="icon"
            className={
              confirmDelete
                ? "text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950"
                : "text-gray-400 hover:text-gray-600"
            }
            onClick={async () => {
              if (!confirmDelete) {
                setConfirmDelete(true);
                setTimeout(() => setConfirmDelete(false), 3000);
                return;
              }
              try {
                await deleteReport.mutateAsync(sessionId);
                router.push("/dashboard");
              } catch (err) {
                alert(
                  `Failed to delete: ${err instanceof Error ? err.message : "Unknown error"}`
                );
                setConfirmDelete(false);
              }
            }}
            disabled={deleteReport.isPending}
            title={
              confirmDelete
                ? "Click again to confirm delete"
                : "Delete this report"
            }
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Badge
          variant={
            report.analysis_status === "completed" ? "default" : "secondary"
          }
        >
          Analysis: {report.analysis_status}
        </Badge>
        {report.analysis_status === "processing" && (
          <Badge variant="outline" className="animate-pulse">
            <Loader2 className="h-3 w-3 mr-1 animate-spin" />
            Processing...
          </Badge>
        )}
        {report.embedding_source && (
          <Badge
            variant="outline"
            className={
              report.embedding_source === "real"
                ? "border-green-300 text-green-700 dark:border-green-700 dark:text-green-400"
                : "border-gray-300 text-gray-500"
            }
          >
            {report.embedding_source === "real"
              ? "✓ Real Embeddings"
              : "Mock Embeddings"}
          </Badge>
        )}
      </div>

      {/* Tabs */}
      <Tabs defaultValue="table">
        <TabsList>
          <TabsTrigger value="table">Condition Table</TabsTrigger>
          <TabsTrigger value="distribution">Score Distribution</TabsTrigger>
          <TabsTrigger value="cluster">Cluster View</TabsTrigger>
        </TabsList>

        <TabsContent value="table">
          {/* ===== FILTER BAR ===== */}
          <div className="space-y-3 mb-4">
            {/* Risk tier pills */}
            <div className="flex flex-wrap items-center gap-2">
              <FilterPill
                label="All"
                count={riskCounts.all}
                dotColor={RISK_DOT_COLORS.all}
                active={riskFilter === "all"}
                onClick={() => setRiskFilter("all")}
              />
              {RISK_TIERS.map((tier) => (
                <FilterPill
                  key={tier}
                  label={tier.charAt(0).toUpperCase() + tier.slice(1)}
                  count={riskCounts[tier]}
                  dotColor={RISK_DOT_COLORS[tier]}
                  active={riskFilter === tier}
                  onClick={() =>
                    setRiskFilter(riskFilter === tier ? "all" : tier)
                  }
                />
              ))}
            </div>

            {/* Search + active filter summary */}
            <div className="flex items-center gap-3">
              <div className="relative max-w-sm flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search conditions..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9 h-9"
                />
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery("")}
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700"
                  >
                    <X className="h-3.5 w-3.5 text-muted-foreground" />
                  </button>
                )}
              </div>

              {/* Results count */}
              <span className="text-sm text-muted-foreground whitespace-nowrap">
                {filteredEntries.length} condition
                {filteredEntries.length !== 1 ? "s" : ""}
                {hasActiveFilters && <> of {report.entries.length}</>}
              </span>

              {/* Clear all filters */}
              {hasActiveFilters && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={clearAllFilters}
                  className="text-xs h-7 px-2"
                >
                  <X className="h-3 w-3 mr-1" />
                  Clear filters
                </Button>
              )}
            </div>

            {/* Active filter badges */}
            {(organFilter.size > 0 || locationFilter.size > 0) && (
              <div className="flex flex-wrap items-center gap-1.5">
                {Array.from(organFilter).map((v) => (
                  <Badge
                    key={`organ-${v}`}
                    variant="secondary"
                    className="cursor-pointer hover:bg-gray-200 dark:hover:bg-gray-700 gap-1 text-xs"
                    onClick={() => toggleSetItem(setOrganFilter, v)}
                  >
                    Organ: {v}
                    <X className="h-3 w-3" />
                  </Badge>
                ))}
                {Array.from(locationFilter).map((v) => (
                  <Badge
                    key={`loc-${v}`}
                    variant="secondary"
                    className="cursor-pointer hover:bg-gray-200 dark:hover:bg-gray-700 gap-1 text-xs"
                    onClick={() => toggleSetItem(setLocationFilter, v)}
                  >
                    Location: {v}
                    <X className="h-3 w-3" />
                  </Badge>
                ))}
              </div>
            )}
          </div>

          {/* ===== TABLE (Sevarthi-inspired styling) ===== */}
          <Card className="overflow-hidden">
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <SortableHead
                      label="Condition"
                      field="condition_name"
                      currentSort={sortField}
                      currentDir={sortDir}
                      onSort={handleSort}
                    />
                    <SortableHead
                      label="Anatomical Location"
                      field="anatomical_location"
                      currentSort={sortField}
                      currentDir={sortDir}
                      onSort={handleSort}
                      filterIcon={
                        <ColumnFilter
                          title="Anatomical Location"
                          options={locationOptions}
                          selected={locationFilter}
                          onToggle={(v) =>
                            toggleSetItem(setLocationFilter, v)
                          }
                          onClear={() => setLocationFilter(new Set())}
                          onSelectAll={() =>
                            selectAll(setLocationFilter, locationOptions)
                          }
                        />
                      }
                    />
                    <SortableHead
                      label="Organ System"
                      field="organ_system"
                      currentSort={sortField}
                      currentDir={sortDir}
                      onSort={handleSort}
                      filterIcon={
                        <ColumnFilter
                          title="Organ System"
                          options={organOptions}
                          selected={organFilter}
                          onToggle={(v) =>
                            toggleSetItem(setOrganFilter, v)
                          }
                          onClear={() => setOrganFilter(new Set())}
                          onSelectAll={() =>
                            selectAll(setOrganFilter, organOptions)
                          }
                        />
                      }
                    />
                    <SortableHead
                      label="Score"
                      field="score"
                      currentSort={sortField}
                      currentDir={sortDir}
                      onSort={handleSort}
                    />
                    <SortableHead
                      label="Risk"
                      field="risk_tier"
                      currentSort={sortField}
                      currentDir={sortDir}
                      onSort={handleSort}
                    />
                    <TableHead className="bg-gray-50 dark:bg-gray-800/60 text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 border-b-2 border-gray-200 dark:border-gray-700">
                      ICD-10
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredEntries.length === 0 ? (
                    <TableRow>
                      <TableCell
                        colSpan={6}
                        className="text-center py-8 text-muted-foreground"
                      >
                        No conditions match the current filters.
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredEntries.map((entry, idx) => (
                      <TableRow
                        key={entry.id}
                        className={
                          idx % 2 === 0
                            ? "bg-white dark:bg-gray-900/20"
                            : "bg-gray-50/50 dark:bg-gray-800/20"
                        }
                      >
                        <TableCell className="font-medium border-l-2 border-l-transparent hover:border-l-blue-500 transition-colors">
                          {entry.condition_name}
                          {entry.marker && (
                            <span className="ml-1 text-xs text-gray-400">
                              #{entry.marker}
                            </span>
                          )}
                        </TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {entry.anatomical_location || "\u2014"}
                        </TableCell>
                        <TableCell className="text-sm">
                          {entry.organ_system || "\u2014"}
                        </TableCell>
                        <TableCell>
                          <ScoreBar score={entry.score} />
                        </TableCell>
                        <TableCell>
                          <RiskBadge tier={entry.risk_tier} />
                        </TableCell>
                        <TableCell className="text-xs font-mono text-gray-500">
                          {entry.condition_icd10 || "\u2014"}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="distribution">
          <OrganSystemAccordion organGroups={organGroups} />
        </TabsContent>

        <TabsContent value="cluster">
          <Card>
            <CardHeader>
              <CardTitle>Cluster Visualization</CardTitle>
              <CardDescription>
                UMAP 2D scatter plot of condition embeddings colored by cluster
              </CardDescription>
            </CardHeader>
            <CardContent>
              {insightsData?.scatter_data && insightsData.scatter_data.length > 0 ? (
                <ClusterScatter data={insightsData.scatter_data} height={400} />
              ) : (
                <div className="flex items-center justify-center h-64 bg-gray-50 dark:bg-gray-800/50 rounded-md">
                  <div className="text-center text-gray-400">
                    <Brain className="h-12 w-12 mx-auto mb-2 opacity-30" />
                    <p className="text-sm">
                      {report.analysis_status === "completed"
                        ? "No cluster data available for this session"
                        : "Run analysis to generate clusters"}
                    </p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
