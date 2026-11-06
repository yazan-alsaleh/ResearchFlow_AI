"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { apiPost } from "@/lib/api";
import type { RunData } from "@/lib/types";

const POPULAR = [
  "AI Engineer",
  "Accountant",
  "Civil Engineer",
  "Marketing Manager",
  "Data Analyst",
  "HR Specialist",
  "Registered Nurse",
  "Project Manager",
];

export default function SearchBox() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function start() {
    const query = title.trim();
    if (query.length < 2 || loading) return;
    setLoading(true);
    setError(null);
    try {
      const idempotencyKey =
        typeof crypto !== "undefined" && "randomUUID" in crypto
          ? crypto.randomUUID()
          : `${Date.now()}-${Math.random()}`;
      const run = await apiPost<RunData>(
        "/api/v1/runs",
        { job_title: query, filters: {} },
        { "Idempotency-Key": idempotencyKey },
      );
      router.push(`/runs/${run.id}`);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not start the run. Is the API running on port 8000?",
      );
      setLoading(false);
    }
  }

  return (
    <div className="card p-5 sm:p-6">
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void start();
        }}
        className="space-y-4"
      >
        <label htmlFor="job-title" className="block text-sm font-semibold text-ink">
          Enter a job title
        </label>
        <div className="flex flex-col gap-3 sm:flex-row">
          <input
            id="job-title"
            className="input"
            placeholder="e.g. AI Engineer, Accountant, Civil Engineer"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            autoComplete="off"
            maxLength={120}
          />
          <button className="btn-primary shrink-0" type="submit" disabled={loading || title.trim().length < 2}>
            {loading ? "Starting…" : "Generate report"}
          </button>
        </div>
        <p className="text-xs text-muted">
          Analyzes the seeded Qatar corpus across all job families. Live source adapters and Arabic
          extraction are on the roadmap.
        </p>
      </form>

      <div className="mt-5 border-t border-line pt-4">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">Popular titles</p>
        <div className="flex flex-wrap gap-2">
          {POPULAR.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setTitle(item)}
              className="rounded-full border border-line bg-white px-3 py-1.5 text-xs font-medium text-ink transition hover:border-maroon/40 hover:text-maroon"
            >
              {item}
            </button>
          ))}
        </div>
      </div>

      {error ? (
        <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}
    </div>
  );
}
