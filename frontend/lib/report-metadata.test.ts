import { describe, expect, it } from "vitest";
import { buildReportMetadata, fallbackReportMetadata } from "./report-metadata";
import type { ReportData } from "./types";

function makeReport(): ReportData {
  return {
    id: "report-1",
    run_id: "run-1",
    query: "Data Analyst",
    status: "published",
    validation_status: "verified",
    corpus_job_count: 12,
    corpus_company_count: 8,
    generated_at: "2026-11-06T00:00:00Z",
    markdown: "# Data Analyst",
    report: {
      title: "Data Analyst — Qatar Market Snapshot",
      query: "Data Analyst",
      generated_at: "2026-11-06T00:00:00Z",
      corpus: {
        jobs: 12,
        companies: 8,
        sources: 1,
        date_range: { start: "2026-10-01", end: "2026-11-01" },
        salary_coverage: 3,
        snapshot: true,
      },
      executive_summary: [],
      sections: [],
      recommendations: [],
      caveats: [],
      insights: {
        top_skills: [
          {
            skill: "SQL",
            category: "technical",
            skill_type: "language",
            jobs: 9,
            pct: 75,
            required_jobs: 8,
            preferred_jobs: 1,
            evidence_ref: "ev_skill_001",
          },
        ],
        degrees: [],
        certifications: [],
        experience: [],
        companies: [],
        languages: [],
        cooccurrence: {
          skills: ["SQL", "Python"],
          matrix: [
            [9, 6],
            [6, 7],
          ],
          pairs: [{ a: "SQL", b: "Python", count: 6, jaccard: 0.6 }],
        },
      },
      evidence_refs: [],
      evidence_jobs: {},
      validation: { status: "verified", checked_claims: 10 },
    },
  } as ReportData;
}

describe("buildReportMetadata", () => {
  it("includes query, top skill, pair, and canonical URL", () => {
    const metadata = buildReportMetadata(makeReport(), "https://example.vercel.app/");
    expect(metadata.title).toContain("Data Analyst");
    expect(metadata.description).toContain("Top skill: SQL (9 ads, 75%)");
    expect(metadata.description).toContain("Often paired with: SQL + Python");
    expect(metadata.description).toContain("evidence-verified");
    expect(metadata.alternates?.canonical).toBe("https://example.vercel.app/reports/report-1");
    const og = metadata.openGraph as { url?: string; siteName?: string };
    expect(og.url).toBe("https://example.vercel.app/reports/report-1");
    expect(og.siteName).toBe("ResearchFlow AI");
    expect((metadata.twitter as { card?: string }).card).toBe("summary");
  });

  it("handles missing insights without crashing", () => {
    const report = makeReport();
    report.report.insights.top_skills = [];
    const metadata = buildReportMetadata(report, "http://localhost:3000");
    expect(metadata.description).toContain("12 ads across 8 companies");
  });
});

describe("fallbackReportMetadata", () => {
  it("returns generic share metadata", () => {
    const metadata = fallbackReportMetadata();
    expect(metadata.title).toContain("ResearchFlow AI");
    expect((metadata.twitter as { card?: string }).card).toBe("summary");
  });
});
