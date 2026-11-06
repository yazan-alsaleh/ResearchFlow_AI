import type { Metadata } from "next";
import type { ReportData } from "./types";

export const SITE_NAME = "ResearchFlow AI";
export const DEFAULT_DESCRIPTION =
  "Evidence-backed analysis of Qatar job ads: skills demand, qualifications, and learning recommendations with cited sources.";

/**
 * Build shareable Open Graph / Twitter metadata for a report page.
 * Pure function so it can be unit-tested without a server.
 */
export function buildReportMetadata(report: ReportData, siteUrl: string): Metadata {
  const { report: data, query } = report;
  const topSkill = data.insights?.top_skills?.[0];
  const topPair = data.insights?.cooccurrence?.pairs?.[0];
  const title = `${query} — Qatar job market snapshot | ${SITE_NAME}`;
  const descriptionParts = [
    `${data.corpus.jobs} ads across ${data.corpus.companies} companies analyzed.`,
  ];
  if (topSkill) {
    descriptionParts.push(
      `Top skill: ${topSkill.skill} (${topSkill.jobs} ads, ${topSkill.pct}%).`,
    );
  }
  if (topPair) {
    descriptionParts.push(`Often paired with: ${topPair.a} + ${topPair.b}.`);
  }
  descriptionParts.push(
    data.validation?.status === "verified"
      ? "Every claim is evidence-verified."
      : "Every claim cites evidence.",
  );
  const description = descriptionParts.join(" ");
  const url = `${siteUrl.replace(/\/$/, "")}/reports/${report.id}`;

  return {
    title,
    description,
    alternates: { canonical: url },
    openGraph: {
      type: "article",
      url,
      siteName: SITE_NAME,
      title,
      description,
    },
    twitter: {
      card: "summary",
      title,
      description,
    },
  };
}

export function fallbackReportMetadata(): Metadata {
  return {
    title: `Report | ${SITE_NAME}`,
    description: DEFAULT_DESCRIPTION,
    twitter: { card: "summary", title: `Report | ${SITE_NAME}`, description: DEFAULT_DESCRIPTION },
  };
}
