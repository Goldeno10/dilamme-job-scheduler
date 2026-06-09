const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ??
  (typeof window !== "undefined" ? "/api/v1" : "http://localhost:8000/api/v1");

export type Priority = 1 | 2 | 3;
export type JobStatus = "pending" | "processing" | "completed" | "failed" | "cancelled";
export type RecurringInterval = "every_1_minute" | "every_5_minutes" | "every_1_hour";

export interface Job {
  id: string;
  type: string;
  payload: Record<string, unknown>;
  priority: Priority;
  status: JobStatus;
  retry_count: number;
  scheduled_at: string | null;
  interval: RecurringInterval | null;
  depends_on: string[];
  error: string | null;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
  in_dlq: boolean;
}

export interface DashboardStats {
  pending: number;
  processing: number;
  completed: number;
  failed: number;
  cancelled: number;
  dlq: number;
  total: number;
}

export interface JobCreate {
  type: string;
  payload: Record<string, unknown>;
  priority: Priority;
  scheduled_at?: string;
  interval?: RecurringInterval;
  depends_on?: string[];
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || res.statusText);
  }
  return res.json();
}

export const api = {
  getStats: () => request<DashboardStats>("/stats"),
  getJobs: (status?: JobStatus) =>
    request<Job[]>(`/jobs${status ? `?status=${status}` : ""}`),
  getJob: (id: string) => request<Job>(`/jobs/${id}`),
  createJob: (data: JobCreate) =>
    request<Job>("/jobs", { method: "POST", body: JSON.stringify(data) }),
  cancelJob: (id: string) =>
    request<Job>(`/jobs/${id}`, { method: "DELETE" }),
  getDlq: () => request<Job[]>("/dlq"),
  retryDlq: (id: string) =>
    request<Job>(`/dlq/${id}/retry`, { method: "POST" }),
  createReportWorkflow: (email_to: string, email_subject?: string) =>
    request<Job[]>("/workflows/report-pipeline", {
      method: "POST",
      body: JSON.stringify({ email_to, email_subject }),
    }),
};

export function eventsUrl(): string {
  return `${API_BASE}/events`;
}
