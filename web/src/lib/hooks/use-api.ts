/**
 * TanStack Query hooks for API data fetching.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import { useEffect, useState } from "react";
import apiClient from "@/lib/api-client";

/**
 * Hook that syncs the NextAuth session token into the API client
 * and returns whether the token is ready.
 */
export function useApiToken(): boolean {
  const { data: session, status } = useSession();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (status === "authenticated" && session) {
      const s = session as unknown as Record<string, unknown>;
      if (s?.accessToken) {
        apiClient.setToken(s.accessToken as string);
        setReady(true);
      }
    } else if (status === "unauthenticated") {
      setReady(false);
    }
  }, [session, status]);

  return ready;
}

export function usePatients() {
  const ready = useApiToken();
  return useQuery({
    queryKey: ["patients"],
    queryFn: () => apiClient.listPatients(),
    staleTime: 5 * 60 * 1000,
    enabled: ready,
  });
}

export function usePatientHistory(patientId: string | null) {
  const ready = useApiToken();
  return useQuery({
    queryKey: ["patient-history", patientId],
    queryFn: () => apiClient.getPatientHistory(patientId!),
    enabled: ready && !!patientId,
    staleTime: 2 * 60 * 1000,
  });
}

export function useReport(sessionId: string | null, opts?: { poll?: boolean }) {
  const ready = useApiToken();
  const query = useQuery({
    queryKey: ["report", sessionId],
    queryFn: () => apiClient.getReport(sessionId!),
    enabled: ready && !!sessionId,
    // Poll every 3s while analysis is in progress
    refetchInterval: opts?.poll
      ? (query) => {
          const status = query.state.data?.analysis_status;
          return status === "processing" || status === "pending" ? 3000 : false;
        }
      : false,
  });
  return query;
}

export function useInsights(sessionId: string | null) {
  const ready = useApiToken();
  return useQuery({
    queryKey: ["insights", sessionId],
    queryFn: () => apiClient.getInsights(sessionId!),
    enabled: ready && !!sessionId,
  });
}

export function useRecoveryPlan(sessionId: string | null) {
  const ready = useApiToken();
  return useQuery({
    queryKey: ["recovery", sessionId],
    queryFn: () => apiClient.getRecoveryPlan(sessionId!),
    enabled: ready && !!sessionId,
    retry: false,
  });
}

export function useUploadReport() {
  return useMutation({
    mutationFn: (file: File) => apiClient.uploadReport(file),
  });
}

export function useAnalyzeReport() {
  return useMutation({
    mutationFn: (sessionId: string) => apiClient.analyzeReport(sessionId),
  });
}

export function useCompareSessions() {
  return useMutation({
    mutationFn: ({
      sessionId1,
      sessionId2,
    }: {
      sessionId1: string;
      sessionId2: string;
    }) => apiClient.compareSessions(sessionId1, sessionId2),
  });
}

export function useDeletePatient() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (patientId: string) => apiClient.deletePatient(patientId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["patients"] });
    },
  });
}
