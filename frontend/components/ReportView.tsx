"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { API_BASE, apiGet } from "@/lib/api";
import type { Claim, EvidenceRef, ReportData, SkillInsight } from "@/lib/types";

function EvidenceChip({ id, onSelect }: { id: string; onSelect: (id: string) => void }) {
  return (
    <button type="button" className="evidence-chip" onClick={() => onSelect(id)} title="Show evidence">
      {id}
    </button>
  );
}

function ClaimLine({ claim, onSelect }: { claim: Claim; onSelect: (id: string) => void }) {
  return (
    <li className="flex flex-wrap items-start gap-2 leading-7 text-ink">
      <span>{claim.text ?? claim.rationale}</span>
      <EvidenceChip id={claim.evidence_ref} onSelect={onSelect} />
    </li>
  );
}

function SkillBar({ skill, maxJobs }: { skill: SkillInsight; maxJobs: number }) {
  const width = Math.max(3, (skill.jobs / maxJobs) * 100);
  const required = (skill.required_jobs / Math.max(skill.jobs, 1)) * 100;
  const preferred = (skill.preferred_jobs / Math.max(skill.jobs, 1)) * 100;
  const mentioned = Math.max(0, 100 - required - preferred);
  return (
    <div>
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-sm font-medium text-ink">{skill.skill}</span>
        <span className="shrink-0 text-xs text-muted">
          {skill.jobs} ads · {skill.pct}%
        </span>
      </div>
      <div className="mt-1.5 flex h-3 w-full overflow-hidden rounded-full bg-sand">
        <div style={{ width: `${width}%` }} className="flex h-full overflow-hidden rounded-full">
          <div style={{ width: `${required}%` }} className="h-full bg-maroon" />
          <div style={{ width: `${preferred}%` }} className="h-full bg-maroon/40" />
          <div style={{ width: `${mentioned}%` }} className="h-full bg-maroon/15" />
        </div>
      </div>
      <p className="mt-1 text-[11px] text-muted">
        {skill.required_jobs} required · {skill.preferred_jobs} preferred
      </p>
    </div>
  );
}

export default function ReportView({ reportId }: { reportId: string }) {
  const [report, setReport] = useState<ReportData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedRef, setSelectedRef] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    apiGet<ReportData>(`/api/v1/reports/${reportId}`)
      .then(setReport)
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load the report."));
  }, [reportId]);

  const refMap = useMemo(() => {
    const map = new Map<string, EvidenceRef>();
    for (const ref of report?.report.evidence_refs ?? []) map.set(ref.id, ref);
    return map;
  }, [report]);

  if (error) {
    return (
      <div className="container-page py-16">
        <div className="card p-8">
          <h1 className="text-xl font-bold text-ink">Report unavailable</h1>
          <p className="mt-2 text-sm text-muted">{error}</p>
          <Link href="/" className="btn-secondary mt-5">
            Back to search
          </Link>
        </div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="container-page py-16">
        <div className="mx-auto max-w-4xl space-y-4">
          <div className="h-10 w-2/3 animate-pulse rounded bg-sand" />
          <div className="h-4 w-1/3 animate-pulse rounded bg-sand" />
          <div className="card h-64 animate-pulse" />
        </div>
      </div>
    );
  }

  const data = report.report;
  const insights = data.insights ?? {
    top_skills: [],
    degrees: [],
    certifications: [],
    experience: [],
    companies: [],
    languages: [],
    cooccurrence: { skills: [], matrix: [], pairs: [] },
  };
  insights.cooccurrence ??= { skills: [], matrix: [], pairs: [] };
  const topSkills = insights.top_skills ?? [];
  const maxJobs = Math.max(...topSkills.map((skill) => skill.jobs), 1);
  const selected = selectedRef ? refMap.get(selectedRef) : null;
  const selectedJobs = (selected?.job_ids ?? [])
    .map((id) => data.evidence_jobs?.[id])
    .filter(Boolean)
    .slice(0, 8);
  const validation = data.validation?.status ?? report.validation_status;
  const isVerified = validation === "verified";

  function selectRef(id: string) {
    setSelectedRef(id);
    setTimeout(() => {
      document.getElementById("evidence-panel")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }, 50);
  }

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="container-page py-10 print:py-0">
      <div className="mx-auto max-w-5xl">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="badge badge-cached">{data.corpus.snapshot ? "Snapshot" : "Live"}</span>
          <span className={`badge ${isVerified ? "badge-verified" : "badge-partial"}`}>
            {isVerified ? "All claims verified" : "Partially verified"}
          </span>
          <span className="badge border-line bg-white text-muted">{report.query}</span>
        </div>

        <div className="mt-4 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="max-w-3xl text-3xl font-black tracking-tight text-ink sm:text-4xl">
              {data.title}
            </h1>
            <p className="mt-2 text-sm text-muted">
              {data.corpus.jobs} ads · {data.corpus.companies} companies · {data.corpus.sources} sources
              {data.corpus.date_range.start ? (
                <>
                  {" "}
                  · {data.corpus.date_range.start} to {data.corpus.date_range.end}
                </>
              ) : null}
            </p>
          </div>
          <div className="no-print flex flex-wrap gap-2">
            <button type="button" className="btn-secondary" onClick={() => void copyLink()}>
              {copied ? "Copied" : "Copy link"}
            </button>
            <a
              className="btn-secondary"
              href={`${API_BASE}/api/v1/reports/${reportId}/markdown`}
              target="_blank"
              rel="noreferrer"
            >
              Download Markdown
            </a>
            <button type="button" className="btn-secondary" onClick={() => window.print()}>
              Print
            </button>
          </div>
        </div>

        <div className="card mt-8 p-6 sm:p-8">
          <h2 className="section-title">Executive summary</h2>
          <ul className="mt-4 space-y-3">
            {data.executive_summary.map((claim, index) => (
              <ClaimLine key={`${claim.evidence_ref}-${index}`} claim={claim} onSelect={selectRef} />
            ))}
          </ul>
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-[1.35fr_0.65fr]">
          <section className="card p-6 sm:p-8">
            <div className="flex items-end justify-between gap-3">
              <div>
                <h2 className="section-title">Most requested skills</h2>
                <p className="mt-1 text-sm text-muted">Share of ads mentioning each skill.</p>
              </div>
              <span className="text-xs text-muted">{data.corpus.jobs} ads</span>
            </div>
            <div className="mt-6 space-y-4">
              {topSkills.length > 0 ? (
                topSkills.map((skill) => <SkillBar key={skill.skill} skill={skill} maxJobs={maxJobs} />)
              ) : (
                <p className="text-sm text-muted">No skills were extracted from this corpus.</p>
              )}
            </div>
            <div className="mt-6 flex flex-wrap gap-4 text-xs text-muted">
              <span className="inline-flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-sm bg-maroon" /> required
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-sm bg-maroon/40" /> preferred
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-sm bg-maroon/15" /> mentioned
              </span>
            </div>
          </section>

          <aside className="space-y-6">
            <section className="card p-6">
              <h2 className="section-title">At a glance</h2>
              <dl className="mt-4 space-y-3 text-sm">
                <div className="flex items-center justify-between gap-3">
                  <dt className="text-muted">Required skills</dt>
                  <dd className="font-semibold text-ink">{data.executive_summary[2] ? "See summary" : "—"}</dd>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <dt className="text-muted">Salary stated</dt>
                  <dd className="font-semibold text-ink">
                    {data.corpus.salary_coverage} / {data.corpus.jobs}
                  </dd>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <dt className="text-muted">Claims checked</dt>
                  <dd className="font-semibold text-ink">{data.validation?.checked_claims ?? "—"}</dd>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <dt className="text-muted">Validation</dt>
                  <dd className={`font-semibold ${isVerified ? "text-emerald-700" : "text-amber-700"}`}>
                    {validation}
                  </dd>
                </div>
              </dl>
            </section>

            <section className="card p-6">
              <h2 className="section-title">Experience mix</h2>
              <div className="mt-4 space-y-3">
                {insights.experience
                  .filter((item) => item.bucket !== "not stated")
                  .map((item) => (
                    <div key={item.bucket} className="flex items-center justify-between gap-3 text-sm">
                      <span className="text-muted">{item.bucket} years</span>
                      <span className="font-semibold text-ink">{item.jobs} ads</span>
                    </div>
                  ))}
                {insights.experience.every((item) => item.bucket === "not stated") ? (
                  <p className="text-sm text-muted">Experience was not stated in these ads.</p>
                ) : null}
              </div>
            </section>
          </aside>
        </div>

        <div className="mt-6 grid gap-6 md:grid-cols-2">
          <section className="card p-6">
            <h2 className="section-title">Degrees</h2>
            <ul className="mt-4 space-y-2 text-sm">
              {insights.degrees.length > 0 ? (
                insights.degrees.map((item) => (
                  <li key={item.level} className="flex items-center justify-between gap-3">
                    <span className="text-muted">{item.level}</span>
                    <span className="font-semibold text-ink">{item.jobs} ads</span>
                  </li>
                ))
              ) : (
                <li className="text-muted">No degree requirement extracted.</li>
              )}
            </ul>
          </section>
          <section className="card p-6">
            <h2 className="section-title">Certifications</h2>
            <ul className="mt-4 space-y-2 text-sm">
              {insights.certifications.length > 0 ? (
                insights.certifications.map((item) => (
                  <li key={item.name} className="flex items-center justify-between gap-3">
                    <span className="text-muted">{item.name}</span>
                    <span className="font-semibold text-ink">{item.jobs} ads</span>
                  </li>
                ))
              ) : (
                <li className="text-muted">No certification requirement extracted.</li>
              )}
            </ul>
          </section>
        </div>

        {insights.cooccurrence.skills.length > 1 ? (
          <section className="card mt-6 p-6 sm:p-8">
            <h2 className="section-title">Skill co-occurrence</h2>
            <p className="mt-1 text-sm text-muted">
              Pairs that appear together in the same ads. Counts are shared ads; Jaccard measures
              overlap relative to either skill alone.
            </p>
            <div className="mt-5 overflow-x-auto">
              <table className="min-w-full text-left text-xs">
                <thead>
                  <tr>
                    <th className="p-2 text-muted">Skill</th>
                    {insights.cooccurrence.skills.map((name) => (
                      <th key={name} className="p-2 font-medium text-muted" title={name}>
                        {name.slice(0, 8)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {insights.cooccurrence.skills.map((name, i) => (
                    <tr key={name} className="border-t border-line">
                      <th className="p-2 font-medium text-ink">{name}</th>
                      {insights.cooccurrence.matrix[i].map((count, j) => (
                        <td
                          key={`${name}-${insights.cooccurrence.skills[j]}`}
                          className="p-2 text-center text-muted"
                          style={{
                            backgroundColor:
                              count === 0
                                ? undefined
                                : `rgba(138, 21, 56, ${0.08 + (count / Math.max(insights.top_skills[0]?.jobs ?? 1, 1)) * 0.3})`,
                          }}
                        >
                          {count}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <ul className="mt-4 space-y-1.5 text-sm">
              {insights.cooccurrence.pairs.slice(0, 5).map((pair) => (
                <li key={`${pair.a}-${pair.b}`} className="text-muted">
                  <span className="font-semibold text-ink">
                    {pair.a} + {pair.b}
                  </span>{" "}
                  — {pair.count} ads (Jaccard {pair.jaccard.toFixed(2)})
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        <section className="card mt-6 p-6 sm:p-8">
          <h2 className="section-title">Learning recommendations</h2>
          <p className="mt-1 text-sm text-muted">
            Prioritized by demand in the corpus. Effort is a rough signal, not a course plan.
          </p>
          <ol className="mt-5 space-y-3">
            {data.recommendations.map((item) => (
              <li key={`${item.priority}-${item.skill}`} className="rounded-xl border border-line bg-[#fbf8f3] p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-ink">
                      {item.priority}. {item.skill}
                    </p>
                    <p className="mt-1 text-sm leading-6 text-muted">{item.rationale}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="badge border-line bg-white text-muted">{item.effort} effort</span>
                    <EvidenceChip id={item.evidence_ref} onSelect={selectRef} />
                  </div>
                </div>
              </li>
            ))}
          </ol>
        </section>

        <section className="card mt-6 p-6 sm:p-8">
          <h2 className="section-title">Detailed findings</h2>
          <div className="mt-4 space-y-6">
            {data.sections.map((section) => (
              <div key={section.heading}>
                <h3 className="font-semibold text-ink">{section.heading}</h3>
                <ul className="mt-2 space-y-2">
                  {section.claims.map((claim, index) => (
                    <ClaimLine key={`${claim.evidence_ref}-${index}`} claim={claim} onSelect={selectRef} />
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>

        <section id="evidence-panel" className="card mt-6 scroll-mt-24 p-6 sm:p-8">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="section-title">Evidence</h2>
              <p className="mt-1 text-sm text-muted">
                Click any evidence chip above to inspect the matching ads and quotes.
              </p>
            </div>
            {selected ? <span className="evidence-chip">{selected.id}</span> : null}
          </div>

          {selected ? (
            <div className="mt-5">
              <div className="rounded-xl border border-line bg-[#fbf8f3] p-4">
                <p className="text-sm font-semibold text-ink">{selected.label}</p>
                <p className="mt-1 text-sm text-muted">
                  Value: <span className="font-mono text-ink">{String(selected.value)}</span> · metric:{" "}
                  <span className="font-mono text-ink">{selected.metric}</span> ·{" "}
                  {selected.job_ids.length} linked ads
                </p>
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                {selectedJobs.map((job) => (
                  <article key={job!.id} className="rounded-xl border border-line bg-white p-4">
                    <p className="text-sm font-semibold text-ink" dir="auto">{job!.title}</p>
                    <p className="mt-1 text-xs text-muted" dir="auto">
                      {job!.company} · {job!.city ?? "Qatar"}
                      {job!.posted_at ? ` · ${job!.posted_at.slice(0, 10)}` : ""}
                    </p>
                    <a
                      href={job!.url}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-2 inline-block text-xs font-semibold text-maroon underline decoration-maroon/30 underline-offset-2"
                    >
                      Open source posting
                    </a>
                  </article>
                ))}
                {selectedJobs.length === 0 ? (
                  <p className="text-sm text-muted">
                    This is an aggregate metric; individual job links are not attached.
                  </p>
                ) : null}
              </div>
            </div>
          ) : (
            <p className="mt-4 text-sm text-muted">
              Select an evidence chip to see the job ads behind a claim.
            </p>
          )}
        </section>

        <section className="card mt-6 p-6 sm:p-8">
          <h2 className="section-title">Limitations</h2>
          <ul className="mt-4 space-y-2 text-sm leading-6 text-muted">
            {data.caveats.map((caveat) => (
              <li key={caveat} className="flex gap-2">
                <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-maroon/50" />
                <span>{caveat}</span>
              </li>
            ))}
          </ul>
          <p className="mt-5 text-xs text-muted">
            Read the{" "}
            <Link href="/about" className="font-semibold text-maroon underline decoration-maroon/30 underline-offset-2">
              methodology
            </Link>{" "}
            for collection policy, de-duplication, model routing, and validation rules.
          </p>
        </section>
      </div>
    </div>
  );
}
