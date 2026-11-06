"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";
import type { RunData } from "@/lib/types";

const STAGES = [
  { key: "collect", label: "Collecting ads" },
  { key: "dedupe", label: "De-duplicating" },
  { key: "extract", label: "Extracting requirements" },
  { key: "aggregate", label: "Aggregating demand" },
  { key: "report", label: "Writing cited report" },
];

const stageIndex = (stage: string) => {
  if (stage === "done" || stage === "queued") return stage === "done" ? STAGES.length : 0;
  const index = STAGES.findIndex((item) => item.key === stage);
  return index === -1 ? 0 : index;
};

export default function RunProgress({ runId }: { runId: string }) {
  const router = useRouter();
  const [run, setRun] = useState<RunData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);

  useEffect(() => {
    let active = true;
    let redirectTimer: ReturnType<typeof setTimeout> | undefined;

    const poll = async () => {
      try {
        const data = await apiGet<RunData>(`/api/v1/runs/${runId}`);
        if (!active) return;
        setRun(data);
        setError(null);
        if (data.report_id && (data.status === "completed" || data.status === "partial")) {
          redirectTimer = setTimeout(() => router.replace(`/reports/${data.report_id}`), 700);
        }
      } catch (err) {
        if (active) setError(err instanceof Error ? err.message : "Could not load the run.");
      }
    };

    void poll();
    const interval = setInterval(() => {
      if (!redirectTimer) void poll();
    }, 1500);
    return () => {
      active = false;
      clearInterval(interval);
      if (redirectTimer) clearTimeout(redirectTimer);
    };
  }, [runId, router]);

  async function cancel() {
    setCancelling(true);
    try {
      const data = await apiPost<RunData>(`/api/v1/runs/${runId}/cancel`, {});
      setRun(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not cancel the run.");
    } finally {
      setCancelling(false);
    }
  }

  if (error && !run) {
    return (
      <div className="container-page py-16">
        <div className="card p-8">
          <h1 className="text-xl font-bold text-ink">Run unavailable</h1>
          <p className="mt-2 text-sm text-muted">{error}</p>
          <Link href="/" className="btn-secondary mt-5">
            Back to search
          </Link>
        </div>
      </div>
    );
  }

  if (!run) {
    return (
      <div className="container-page py-16">
        <div className="card p-8">
          <div className="h-5 w-48 animate-pulse rounded bg-sand" />
          <div className="mt-4 h-3 w-full animate-pulse rounded bg-sand" />
        </div>
      </div>
    );
  }

  const current = stageIndex(run.stage);
  const total = Math.max(run.progress.jobs_collected, 1);
  const progressPct = Math.min(100, Math.round((run.progress.jobs_extracted / total) * 100));
  const ready = Boolean(run.report_id) && (run.status === "completed" || run.status === "partial");

  return (
    <div className="container-page py-12">
      <div className="mx-auto max-w-3xl">
        <p className="text-xs font-semibold uppercase tracking-wide text-maroon">Research run</p>
        <div className="mt-2 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-black tracking-tight text-ink">{run.query}</h1>
            <p className="mt-1 text-sm text-muted">
              Run <span className="font-mono text-xs">{run.id.slice(0, 8)}</span> · {run.mode} mode
            </p>
          </div>
          <span
            className={`badge ${
              run.status === "failed"
                ? "border-red-200 bg-red-50 text-red-700"
                : run.status === "partial"
                  ? "badge-partial"
                  : run.status === "completed"
                    ? "badge-verified"
                    : "badge-live"
            }`}
          >
            {run.status}
          </span>
        </div>

        <div className="card mt-6 p-6">
          <div className="flex items-center justify-between text-sm">
            <span className="font-semibold text-ink">{STAGES[Math.min(current, STAGES.length - 1)]?.label}</span>
            <span className="text-muted">
              {run.progress.jobs_extracted} / {run.progress.jobs_collected} ads extracted
            </span>
          </div>
          <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-sand">
            <div className="h-full rounded-full bg-maroon transition-all duration-500" style={{ width: `${progressPct}%` }} />
          </div>

          <ol className="mt-6 space-y-3">
            {STAGES.map((stage, index) => {
              const done = index < current;
              const active = index === current && run.status === "running";
              return (
                <li key={stage.key} className="flex items-center gap-3 text-sm">
                  <span
                    className={`grid h-7 w-7 shrink-0 place-items-center rounded-full border text-xs font-bold ${
                      done
                        ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                        : active
                          ? "border-maroon bg-maroon text-white"
                          : "border-line bg-white text-muted"
                    }`}
                  >
                    {done ? "✓" : index + 1}
                  </span>
                  <span className={done || active ? "font-medium text-ink" : "text-muted"}>{stage.label}</span>
                  {active ? <span className="ml-auto text-xs text-maroon">in progress</span> : null}
                </li>
              );
            })}
          </ol>

          <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              ["Collected", run.progress.jobs_collected],
              ["Deduplicated", run.progress.jobs_deduplicated],
              ["Extracted", run.progress.jobs_extracted],
              ["Failed", run.progress.jobs_failed],
            ].map(([label, value]) => (
              <div key={String(label)} className="rounded-xl border border-line bg-[#fbf8f3] p-3">
                <p className="text-lg font-bold text-ink">{value}</p>
                <p className="text-[11px] uppercase tracking-wide text-muted">{label}</p>
              </div>
            ))}
          </div>

          {run.warnings.length > 0 ? (
            <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
              <p className="font-semibold">Partial results</p>
              <ul className="mt-1 list-inside list-disc space-y-1">
                {run.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {run.status === "failed" ? (
            <div className="mt-5 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
              <p className="font-semibold">Run failed</p>
              <p className="mt-1">{run.error ?? "An unexpected error occurred."}</p>
            </div>
          ) : null}

          <div className="mt-6 flex flex-wrap items-center gap-3">
            {ready ? (
              <Link href={`/reports/${run.report_id}`} className="btn-primary">
                Open the report
              </Link>
            ) : null}
            {run.status === "queued" || run.status === "running" ? (
              <button type="button" className="btn-secondary" onClick={() => void cancel()} disabled={cancelling}>
                {cancelling ? "Cancelling…" : "Cancel run"}
              </button>
            ) : null}
            <Link href="/" className="btn-secondary">
              New search
            </Link>
          </div>
        </div>

        {error ? <p className="mt-4 text-sm text-red-700">{error}</p> : null}
      </div>
    </div>
  );
}
