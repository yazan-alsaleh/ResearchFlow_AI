import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import CoverageStats from "./CoverageStats";

vi.mock("@/lib/api", () => ({
  apiGet: vi.fn(),
}));

import { apiGet } from "@/lib/api";

const apiGetMock = vi.mocked(apiGet);

describe("CoverageStats", () => {
  it("shows live coverage stats when the API responds", async () => {
    apiGetMock.mockResolvedValue({
      total_jobs: 63,
      total_companies: 21,
      total_sources: 1,
      by_family: { software_data: 6, finance: 6 },
      by_source: { seed: 63 },
      latest_collected_at: null,
    });

    render(<CoverageStats />);
    await waitFor(() => expect(screen.getByText("63")).toBeInTheDocument());
    expect(screen.getByText("21")).toBeInTheDocument();
  });

  it("falls back to seeded corpus stats and warns when the API is down", async () => {
    apiGetMock.mockRejectedValue(new Error("down"));

    render(<CoverageStats />);
    await waitFor(() =>
      expect(
        screen.getByText("Live coverage is unavailable. Start the API to load corpus statistics."),
      ).toBeInTheDocument(),
    );
    expect(screen.getByText("63")).toBeInTheDocument();
  });
});
