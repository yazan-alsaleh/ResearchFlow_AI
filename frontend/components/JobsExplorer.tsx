"use client";

import { useEffect, useMemo, useState } from "react";
import { apiGet } from "@/lib/api";
import type { JobData, JobDetail } from "@/lib/types";

const FAMILIES = [
  ["", "All families"],
  ["software_data", "Software & data"],
  ["finance", "Finance & accounting"],
  ["engineering", "Engineering"],
  ["marketing", "Marketing"],
  ["hr", "Human resources"],
  ["healthcare", "Healthcare"],
  ["education", "Education"],
  ["sales", "Sales"],
  ["admin", "Administration"],
  ["legal", "Legal"],
  ["logistics", "Logistics"],
  ["project_management", "Project management"],
  ["business", "Business"],
  ["design", "Design"],
  ["customer_service", "Customer service"],
  ["operations", "Operations"],
  ["procurement", "Procurement"],
];

type ExtractedSkill = {
  name: string;
  importance: string;
  evidence_quote: string;
  category?: string;
};

type ExtractionShape = {
  skills?: ExtractedSkill[];
  experience?: { min_years?: number | null; evidence_quote?: string } | null;
  qualifications?: { value: string; required?: boolean }[];
} | null;

export default function JobsExplorer() {
  const [jobs, setJobs] = useState<JobData[]>([]);
  const [query, setQuery] = useState("");
  const [family, setFamily] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<JobDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    let active = true;
    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const params = new URLSearchParams({ limit: "60" });
        if (query.trim()) params.set("q", query.trim());
        if (family) params.set("family", family);
        const data = await apiGet<{ items: JobData[] }>(`/api/v1/jobs?${params.toString()}`);
        if (active) {
          setJobs(data.items);
          setError(null);
        }
      } catch (err) {
        if (active) setError(err instanceof Error ? err.message : "Could not load jobs.");
      } finally {
        if (active) setLoading(false);
      }
    }, 250);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [query, family]);

  const extraction = useMemo<ExtractionShape>(
    () => (selected?.extraction as ExtractionShape) ?? null,
    [selected],
  );

  async function openJob(job: JobData) {
    setDetailLoading(true);
    try {
      const detail = await apiGet<JobDetail>(`/api/v1/jobs/${job.id}`);
      setSelected(detail);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load the job.");
    } finally {
      setDetailLoading(false);
    }
  }

  return (
    <div className="container-page py-10">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-maroon">Corpus</p>
          <h1 className="mt-2 text-3xl font-black tracking-tight text-ink">Browse Qatar job ads</h1>
          <p className="mt-2 max-w-2xl text-sm text-muted">
            Inspect the ads behind every report. The MVP uses a seeded, cross-sector corpus; live
            source adapters are the next phase.
          </p>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            className="input sm:w-72"
            aria-label="Search jobs"
            placeholder="Search title, company, description"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <select className="input sm:w-52" value={family} onChange={(event) => setFamily(event.target.value)}>
            {FAMILIES.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <p className="mt-4 text-xs text-muted">
        {loading ? "Loading…" : `${jobs.length} ads shown`} · click a row for the full description and
        extraction.
      </p>

      {error ? (
        <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>
      ) : null}

      <div className="mt-4 overflow-hidden rounded-2xl border border-line bg-white shadow-card">
        <div className="hidden grid-cols-[1.6fr_1fr_0.8fr_0.7fr] gap-4 border-b border-line bg-[#fbf8f3] px-5 py-3 text-[11px] font-semibold uppercase tracking-wide text-muted md:grid">
          <span>Role</span>
          <span>Company</span>
          <span>Location</span>
          <span>Posted</span>
        </div>
        <div className="divide-y divide-line">
          {jobs.map((job) => (
            <button
              key={job.id}
              type="button"
              onClick={() => void openJob(job)}
              className="grid w-full grid-cols-1 gap-1 px-5 py-4 text-left transition hover:bg-[#fbf8f3] md:grid-cols-[1.6fr_1fr_0.8fr_0.7fr] md:items-center md:gap-4"
            >
              <span>
                <span className="block text-sm font-semibold text-ink">{job.title}</span>
                <span className="mt-0.5 block text-xs text-muted md:hidden">
                  {job.company} · {job.city ?? job.location_text}
                </span>
              </span>
              <span className="hidden text-sm text-muted md:block">{job.company}</span>
              <span className="hidden text-sm text-muted md:block">{job.city ?? job.location_text}</span>
              <span className="hidden text-xs text-muted md:block">
                {job.posted_at ? job.posted_at.slice(0, 10) : "—"}
              </span>
            </button>
          ))}
          {!loading && jobs.length === 0 ? (
            <p className="px-5 py-10 text-center text-sm text-muted">No ads match this filter.</p>
          ) : null}
        </div>
      </div>

      {selected || detailLoading ? (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-ink/40 p-0 sm:items-center sm:p-6">
          <div className="max-h-[92vh] w-full max-w-3xl overflow-y-auto rounded-t-2xl bg-white p-6 shadow-2xl sm:rounded-2xl">
            {detailLoading || !selected ? (
              <p className="text-sm text-muted">Loading job…</p>
            ) : (
              <>
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h2 className="text-xl font-bold text-ink">{selected.title}</h2>
                    <p className="mt-1 text-sm text-muted">
                      {selected.company} · {selected.location_text}
                    </p>
                  </div>
                  <button
                    type="button"
                    className="rounded-lg border border-line px-3 py-1.5 text-sm font-semibold text-muted hover:text-ink"
                    onClick={() => setSelected(null)}
                  >
                    Close
                  </button>
                </div>

                <div className="mt-4 flex flex-wrap gap-2 text-xs">
                  <span className="badge border-line bg-white text-muted">{selected.job_family}</span>
                  <span className="badge border-line bg-white text-muted">{selected.language}</span>
                  {selected.employment_type ? (
                    <span className="badge border-line bg-white text-muted">{selected.employment_type}</span>
                  ) : null}
                  <a
                    href={selected.url}
                    target="_blank"
                    rel="noreferrer"
                    className="badge border-maroon/20 bg-maroon/5 text-maroon"
                  >
                    Source posting ↗
                  </a>
                </div>

                {extraction?.skills?.length ? (
                  <div className="mt-5">
                    <h3 className="text-sm font-semibold text-ink">Extracted skills</h3>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {extraction.skills.slice(0, 20).map((skill) => (
                        <span
                          key={skill.name}
                          className={`badge ${
                            skill.importance === "required"
                              ? "border-maroon/20 bg-maroon/5 text-maroon"
                              : "border-line bg-white text-muted"
                          }`}
                          title={skill.evidence_quote}
                        >
                          {skill.name}
                          <span className="text-[10px] opacity-70">{skill.importance}</span>
                        </span>
                      ))}
                    </div>
                  </div>
                ) : null}

                <div className="mt-5">
                  <h3 className="text-sm font-semibold text-ink">Description</h3>
                  <p className="mt-2 whitespace-pre-line text-sm leading-7 text-muted">
                    {selected.description}
                  </p>
                </div>
              </>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
