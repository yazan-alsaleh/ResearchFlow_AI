import type { Metadata } from "next";
import ReportView from "@/components/ReportView";
import { API_BASE } from "@/lib/api";
import { buildReportMetadata, fallbackReportMetadata } from "@/lib/report-metadata";
import type { ReportData } from "@/lib/types";

const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/$/, "") ?? "http://localhost:3000";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  try {
    const response = await fetch(`${API_BASE}/api/v1/reports/${id}`, {
      cache: "no-store",
    });
    if (!response.ok) return fallbackReportMetadata();
    const report = (await response.json()) as ReportData;
    return buildReportMetadata(report, SITE_URL);
  } catch {
    return fallbackReportMetadata();
  }
}

export default async function ReportPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ReportView reportId={id} />;
}
