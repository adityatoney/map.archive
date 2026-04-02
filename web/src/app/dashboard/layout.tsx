"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSession } from "next-auth/react";
import { redirect } from "next/navigation";
import { signOut } from "next-auth/react";
import { useEffect, useState } from "react";
import {
  Activity,
  LayoutDashboard,
  FileUp,
  TrendingUp,
  Brain,
  Heart,
  Microscope,
  GitCompare,
  LogOut,
  Sun,
  Moon,
  Menu,
  AlertTriangle,
  Trash2,
  Settings,
} from "lucide-react";
import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { usePatientStore } from "@/lib/stores/patient-store";
import { useUIStore } from "@/lib/stores/ui-store";
import { usePatients, useApiToken, useDeletePatient } from "@/lib/hooks/use-api";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { href: "/dashboard/upload", label: "Upload Scan", icon: FileUp },
  { href: "/dashboard/compare", label: "Compare", icon: GitCompare },
  { href: "/dashboard/settings", label: "Settings", icon: Settings },
];

const DYNAMIC_NAV_ITEMS = [
  { href: "/dashboard/trends", label: "Trends", icon: TrendingUp },
  { href: "/dashboard/insights", label: "Insights", icon: Brain },
  { href: "/dashboard/clinical-analysis", label: "Clinical Analysis", icon: Microscope },
  { href: "/dashboard/recovery", label: "Recovery Plan", icon: Heart },
];

function SidebarNav() {
  const pathname = usePathname();
  const { selectedPatientId, latestSessionId } = usePatientStore();

  return (
    <nav className="space-y-1 px-2">
      {NAV_ITEMS.map((item) => {
        const isActive =
          pathname === item.href ||
          (item.href !== "/dashboard" && pathname.startsWith(item.href));
        const Icon = item.icon;
        return (
          <Link
            key={item.href}
            href={item.href}
            className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
              isActive
                ? "bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300"
                : "text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
            }`}
          >
            <Icon className="h-4 w-4" />
            {item.label}
          </Link>
        );
      })}

      <div className="pt-4 pb-2">
        <p className="px-3 text-xs font-semibold uppercase text-gray-500 dark:text-gray-400">
          Analysis
        </p>
      </div>

      {DYNAMIC_NAV_ITEMS.map((item) => {
        const Icon = item.icon;
        const disabled = !selectedPatientId;
        // Build session-specific href for analysis pages
        const href = latestSessionId
          ? `${item.href}/${latestSessionId}`
          : item.href;

        if (disabled || !latestSessionId) {
          return (
            <span
              key={item.href}
              className="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-gray-400 dark:text-gray-600 cursor-not-allowed"
            >
              <Icon className="h-4 w-4" />
              {item.label}
              <span className="text-xs text-gray-400">
                {!selectedPatientId ? "(select patient)" : "(no scans)"}
              </span>
            </span>
          );
        }

        const isActive = pathname.startsWith(item.href);
        return (
          <Link
            key={item.href}
            href={href}
            className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
              isActive
                ? "bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300"
                : "text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
            }`}
          >
            <Icon className="h-4 w-4" />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}

function PatientSelector() {
  const { selectedPatientId, setSelectedPatientId, setPatients } =
    usePatientStore();
  const { data: patients, refetch } = usePatients();
  const deletePatient = useDeletePatient();
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    if (patients) {
      setPatients(patients);
      if (!selectedPatientId && patients.length > 0) {
        setSelectedPatientId(patients[0].id);
      }
      // If selected patient was deleted, clear selection
      if (
        selectedPatientId &&
        !patients.find((p) => p.id === selectedPatientId)
      ) {
        setSelectedPatientId(patients.length > 0 ? patients[0].id : null);
      }
    }
  }, [patients, selectedPatientId, setPatients, setSelectedPatientId]);

  async function handleDelete() {
    if (!selectedPatientId) return;
    if (!confirmDelete) {
      setConfirmDelete(true);
      // Auto-reset confirmation after 3 seconds
      setTimeout(() => setConfirmDelete(false), 3000);
      return;
    }
    try {
      await deletePatient.mutateAsync(selectedPatientId);
      setConfirmDelete(false);
      setSelectedPatientId(null);
      // refetch is handled by onSuccess in useDeletePatient (invalidates query)
    } catch (err) {
      console.error("Failed to delete patient:", err);
      setConfirmDelete(false);
      alert(`Failed to delete patient: ${err instanceof Error ? err.message : "Unknown error"}`);
    }
  }

  return (
    <div className="flex items-center gap-1">
      <Select
        value={selectedPatientId || ""}
        onValueChange={(v) => {
          setSelectedPatientId(v);
          setConfirmDelete(false);
        }}
      >
        <SelectTrigger className="w-[220px]">
          <SelectValue placeholder="Select patient..." />
        </SelectTrigger>
        <SelectContent>
          {patients?.map((p) => (
            <SelectItem key={p.id} value={p.id}>
              {p.first_name} {p.last_name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {selectedPatientId && (
        <Button
          variant="ghost"
          size="icon"
          className={`h-8 w-8 ${
            confirmDelete
              ? "text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950"
              : "text-gray-400 hover:text-gray-600"
          }`}
          onClick={handleDelete}
          disabled={deletePatient.isPending}
          title={confirmDelete ? "Click again to confirm delete" : "Delete patient"}
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      )}
    </div>
  );
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { data: session, status } = useSession();
  const { theme, setTheme } = useTheme();
  // UI store for sidebar collapse state (used in Phase 5)
  void useUIStore;

  // Sync API token from session (handled by useApiToken hook in use-api.ts)
  useApiToken();

  if (status === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Activity className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (status === "unauthenticated") {
    redirect("/login");
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      {/* Header */}
      <header className="sticky top-0 z-40 border-b bg-white dark:bg-gray-900 dark:border-gray-800">
        <div className="flex h-14 items-center gap-4 px-4">
          {/* Mobile menu */}
          <Sheet>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" className="md:hidden">
                <Menu className="h-5 w-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-64 p-0 pt-10">
              <SidebarNav />
            </SheetContent>
          </Sheet>

          {/* Logo */}
          <Link href="/dashboard" className="flex items-center gap-2">
            <Activity className="h-6 w-6 text-blue-600" />
            <span className="font-bold text-lg hidden sm:inline">
              MedBed Insight
            </span>
          </Link>

          {/* Patient selector */}
          <div className="ml-4">
            <PatientSelector />
          </div>

          {/* Right side */}
          <div className="ml-auto flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            >
              <Sun className="h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
              <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
              <span className="sr-only">Toggle theme</span>
            </Button>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon">
                  <Avatar className="h-7 w-7">
                    <AvatarFallback className="text-xs">
                      {session?.user?.email?.[0]?.toUpperCase() || "U"}
                    </AvatarFallback>
                  </Avatar>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem disabled className="text-xs text-gray-500">
                  {session?.user?.email}
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => signOut()}>
                  <LogOut className="h-4 w-4 mr-2" />
                  Sign Out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </header>

      <div className="flex">
        {/* Sidebar — desktop */}
        <aside className="hidden md:flex w-60 flex-col border-r bg-white dark:bg-gray-900 dark:border-gray-800 min-h-[calc(100vh-3.5rem)] sticky top-14">
          <div className="flex-1 py-4">
            <SidebarNav />
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1 p-6 pb-20">{children}</main>
      </div>

      {/* Medical Disclaimer Banner — fixed, non-dismissible */}
      <div
        className="fixed bottom-0 left-0 right-0 z-50 bg-amber-50 dark:bg-amber-950/80 border-t border-amber-200 dark:border-amber-800 px-4 py-2"
        role="alert"
        aria-label="Medical disclaimer"
      >
        <div className="flex items-center gap-2 max-w-screen-xl mx-auto">
          <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400 flex-shrink-0" />
          <p className="text-xs text-amber-800 dark:text-amber-200">
            <strong>Disclaimer:</strong> MedBed Insight is an analytical
            exploration tool, not a medical diagnostic device. The information
            presented does not constitute medical advice, diagnosis, or treatment
            recommendations. Always consult a qualified healthcare professional
            before making health decisions based on this data.
          </p>
        </div>
      </div>
    </div>
  );
}
