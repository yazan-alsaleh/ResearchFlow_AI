import { afterEach, describe, expect, it, vi } from "vitest";
import { apiGet, apiPost } from "./api";

function mockResponse(body: unknown, ok = true, status = 200) {
  return {
    ok,
    status,
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(typeof body === "string" ? body : JSON.stringify(body)),
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("apiGet", () => {
  it("returns parsed JSON for a successful request", async () => {
    const fetchMock = vi.fn().mockResolvedValue(mockResponse({ status: "ok" }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(apiGet("/api/v1/health")).resolves.toEqual({ status: "ok" });
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/health"),
      expect.objectContaining({ cache: "no-store" }),
    );
  });

  it("throws with the response body on HTTP errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(mockResponse("Run not found", false, 404)),
    );

    await expect(apiGet("/api/v1/runs/nope")).rejects.toThrowError("Run not found");
  });
});

describe("apiPost", () => {
  it("posts JSON with custom headers", async () => {
    const fetchMock = vi.fn().mockResolvedValue(mockResponse({ id: "run-1" }, true, 202));
    vi.stubGlobal("fetch", fetchMock);

    await apiPost("/api/v1/runs", { job_title: "Data Analyst" }, { "Idempotency-Key": "k1" });

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/runs"),
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json", "Idempotency-Key": "k1" },
        body: JSON.stringify({ job_title: "Data Analyst" }),
      }),
    );
  });

  it("throws on failed requests", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(mockResponse("Rate limit exceeded", false, 429)),
    );

    await expect(apiPost("/api/v1/runs", {})).rejects.toThrowError("Rate limit exceeded");
  });
});
