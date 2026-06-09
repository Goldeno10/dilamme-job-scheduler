"use client";

import type { Job } from "@/lib/api";

const PRIORITY_LABELS: Record<number, string> = { 1: "High", 2: "Medium", 3: "Low" };
const PRIORITY_CLASS: Record<number, string> = {
  1: "priority-high",
  2: "priority-medium",
  3: "priority-low",
};

function formatDate(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}

export function JobsTable({
  jobs,
  onCancel,
  showError = false,
  onRetry,
}: {
  jobs: Job[];
  onCancel?: (id: string) => void;
  showError?: boolean;
  onRetry?: (id: string) => void;
}) {
  if (jobs.length === 0) {
    return <p style={{ color: "var(--muted)" }}>No jobs found.</p>;
  }

  return (
    <div style={{ overflowX: "auto" }}>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Type</th>
            <th>Priority</th>
            <th>Status</th>
            <th>Retries</th>
            <th>Scheduled</th>
            <th>Interval</th>
            <th>Created</th>
            {showError && <th>Error</th>}
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <tr key={job.id}>
              <td title={job.id}>{job.id.slice(0, 8)}…</td>
              <td>{job.type}</td>
              <td className={PRIORITY_CLASS[job.priority]}>{PRIORITY_LABELS[job.priority]}</td>
              <td><span className={`badge badge-${job.status}`}>{job.status}</span></td>
              <td>{job.retry_count}</td>
              <td>{formatDate(job.scheduled_at)}</td>
              <td>{job.interval || "—"}</td>
              <td>{formatDate(job.created_at)}</td>
              {showError && (
                <td className="error-text">{job.error || "—"}</td>
              )}
              <td style={{ display: "flex", gap: "0.4rem" }}>
                {onRetry && job.in_dlq && (
                  <button className="btn-primary" onClick={() => onRetry(job.id)}>Retry</button>
                )}
                {onCancel && ["pending", "processing"].includes(job.status) && (
                  <button className="btn-danger" onClick={() => onCancel(job.id)}>Cancel</button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
