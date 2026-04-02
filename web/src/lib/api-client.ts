/**
 * Typed API client for the MedBed Insight FastAPI backend.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ---------- Types ----------

export interface Patient {
  id: string;
  first_name: string;
  last_name: string;
  middle_name?: string | null;
  age?: number | null;
  birthday?: string | null;
  blood_group?: string | null;
}

export interface ScanEntry {
  id: string;
  condition_name: string;
  condition_icd10?: string | null;
  condition_snomed?: string | null;
  anatomical_location?: string | null;
  organ_system?: string | null;
  report_section?: string | null;
  score: number;
  green_ratio?: number | null;
  red_ratio?: number | null;
  marker?: string | null;
  cluster_id?: number | null;
  risk_tier?: string | null;
}

export interface ScanSession {
  id: string;
  patient_id: string;
  scan_date: string;
  report_generated_at?: string | null;
  report_type: string;
  analysis_status: string;
  organ_system?: string | null;
  embedding_source?: string | null;
  entry_count: number;
  entries: ScanEntry[];
}

export interface PatientHistory {
  patient: Patient;
  sessions: {
    id: string;
    scan_date: string;
    report_type: string;
    analysis_status: string;
    organ_system?: string | null;
    entry_count: number;
  }[];
  total_sessions: number;
}

export interface ClusterInfo {
  cluster_id: number;
  conditions: string[];
  avg_score: number;
  risk_tier?: string | null;
  shared_pathways: string[];
  confidence: number;
}

export interface InsightsData {
  session_id: string;
  analysis_status: string;
  clusters: ClusterInfo[];
  patterns: {
    pattern_name: string;
    member_conditions: string[];
    shared_pathways: string[];
    confidence_score: number;
    description: string;
  }[];
  risk_summary: Record<string, {
    avg_score: number;
    condition_count: number;
    risk_tier: string;
  }>;
  umap_coords?: number[][] | null;
  embedding_source?: string | null;
  disclaimer: string;
}

export interface RecoveryPlan {
  id: string;
  session_id: string;
  patient_id: string;
  generated_at: string;
  summary?: string | null;
  organ_system_breakdown?: Record<string, unknown>[] | null;
  priority_conditions?: Record<string, unknown>[] | null;
  recommended_interventions?: Record<string, unknown>[] | null;
  lifestyle_recommendations?: Record<string, unknown>[] | null;
  nutritional_recommendations?: Record<string, unknown>[] | null;
  monitoring_plan?: Record<string, unknown> | null;
  disclaimer: string;
}

export interface CompareResult {
  session_1_id: string;
  session_1_date: string;
  session_2_id: string;
  session_2_date: string;
  deltas: {
    condition_name: string;
    organ_system?: string | null;
    score_1?: number | null;
    score_2?: number | null;
    delta?: number | null;
    status: string;
  }[];
  organ_system_summary: Record<string, unknown>;
  new_conditions: string[];
  resolved_conditions: string[];
}

export interface UploadResult {
  session_id: string;
  patient_id: string;
  entry_count: number;
  message: string;
}

export interface RiskConfig {
  id: string;
  score_mode: "inverted" | "normal";
  tier_thresholds: Record<string, [number, number]>;
  name: string;
  is_active: boolean;
}

export interface RiskConfigUpdate {
  score_mode?: "inverted" | "normal";
  tier_thresholds?: Record<string, [number, number]>;
  name?: string;
}

export interface LoginResult {
  access_token: string;
  token_type: string;
  user_id: string;
  email: string;
}

// ---------- API Client ----------

class ApiClient {
  private token: string | null = null;

  setToken(token: string) {
    this.token = token;
  }

  hasToken(): boolean {
    return !!this.token;
  }

  private async fetch<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string>),
    };

    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }

    // Don't set Content-Type for FormData (let browser set multipart boundary)
    if (!(options.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
    }

    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
    });

    if (res.status === 401) {
      // Token expired — redirect to login if running in browser
      if (typeof window !== "undefined") {
        window.location.href = "/login?error=SessionExpired";
      }
      throw new Error("Unauthorized");
    }

    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(error.detail || `API error: ${res.status}`);
    }

    return res.json();
  }

  // Auth
  async login(email: string, password: string): Promise<LoginResult> {
    return this.fetch("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  }

  // Patients
  async listPatients(): Promise<Patient[]> {
    return this.fetch("/api/v1/patients/");
  }

  async getPatientHistory(patientId: string): Promise<PatientHistory> {
    return this.fetch(`/api/v1/patients/${patientId}/history`);
  }

  async deletePatient(patientId: string): Promise<{ detail: string }> {
    return this.fetch(`/api/v1/patients/${patientId}`, {
      method: "DELETE",
    });
  }

  getReportDownloadUrl(sessionId: string): string {
    return `${API_BASE}/api/v1/reports/${sessionId}/download`;
  }

  async downloadReport(sessionId: string): Promise<void> {
    const headers: Record<string, string> = {};
    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }
    const res = await fetch(`${API_BASE}/api/v1/reports/${sessionId}/download`, { headers });
    if (!res.ok) {
      throw new Error(`Download failed: ${res.status}`);
    }
    const blob = await res.blob();
    const disposition = res.headers.get("content-disposition");
    const filename = disposition?.match(/filename="?([^"]+)"?/)?.[1] || `report-${sessionId}.pdf`;
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  // Reports
  async uploadReport(file: File): Promise<UploadResult> {
    const formData = new FormData();
    formData.append("file", file);
    return this.fetch("/api/v1/reports/upload", {
      method: "POST",
      body: formData,
    });
  }

  async getReport(sessionId: string): Promise<ScanSession> {
    return this.fetch(`/api/v1/reports/${sessionId}`);
  }

  async analyzeReport(sessionId: string): Promise<{ task_id: string; session_id: string; status: string }> {
    return this.fetch(`/api/v1/reports/${sessionId}/analyze`, {
      method: "POST",
    });
  }

  async deleteReport(sessionId: string): Promise<{ detail: string }> {
    return this.fetch(`/api/v1/reports/${sessionId}`, {
      method: "DELETE",
    });
  }

  // Insights
  async getInsights(sessionId: string): Promise<InsightsData> {
    return this.fetch(`/api/v1/insights/${sessionId}`);
  }

  // Recovery
  async getRecoveryPlan(sessionId: string): Promise<RecoveryPlan> {
    return this.fetch(`/api/v1/recovery/${sessionId}`);
  }

  // Compare
  async compareSessions(
    sessionId1: string,
    sessionId2: string
  ): Promise<CompareResult> {
    return this.fetch("/api/v1/reports/compare", {
      method: "POST",
      body: JSON.stringify({
        session_id_1: sessionId1,
        session_id_2: sessionId2,
      }),
    });
  }

  // Admin — Risk Config
  async getRiskConfig(): Promise<RiskConfig> {
    return this.fetch("/api/v1/admin/risk-config");
  }

  async updateRiskConfig(update: RiskConfigUpdate): Promise<RiskConfig> {
    return this.fetch("/api/v1/admin/risk-config", {
      method: "PUT",
      body: JSON.stringify(update),
    });
  }

  // Health
  async healthCheck(): Promise<Record<string, unknown>> {
    return this.fetch("/health");
  }
}

export const apiClient = new ApiClient();
export default apiClient;
