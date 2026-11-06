"use client";

import { useEffect, useState } from "react";
import { apiGet } from "@/lib/api";

type Coverage = {
  total_jobs: number;
  total_companies: number;
  total_sources: number;
  by_family: Record<string, number>;
  by_source: Record<string, number>;
  latest_collected_at: string | null;
};

export default function CoverageStats() {
  const [coverage, setCoverage] = useState<Coverage | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    apiGet<Coverage>("/api/v1/meta/coverage")
      .then(setCoverage)
      .catch(() => setError(true));
  }, []);

  const items = coverage
    ? [
        { label: "Job ads", value: coverage.total_jobs },
        { label: "Companies", value: coverage.total_companies },
        { label: "Sources", value: coverage.total_sources },
        {
          label: "Job families",
          value: Object.keys(coverage.by_family ?? {}).length,
        },
      ]
    : [
        { label: "Job ads", value: 24 },
        { label: "Companies", value: 14 },
        { label: "Sources", value: 1 },
        { label: "Job families", value: 15 },
      ];

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {items.map((item) => (
        <div key={item.label} className="card p-4">
          <p className="text-2xl font-bold tracking-tight text-ink">{item.value}</p>
          <p className="mt-1 text-xs font-medium uppercase tracking-wide text-muted">{item.label}</p>
        </div>
      ))}
      {error ? (
        <p className="col-span-full text-xs text-amber-700">
          Live coverage is unavailable. Start the API to load corpus statistics.
        </p>
      ) : null}
    </div>
  );
}
