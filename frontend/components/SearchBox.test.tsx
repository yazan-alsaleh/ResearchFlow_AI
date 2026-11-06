import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import SearchBox from "./SearchBox";

const pushMock = vi.fn();
const apiPostMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

vi.mock("@/lib/api", () => ({
  apiPost: (...args: unknown[]) => apiPostMock(...args),
}));

beforeEach(() => {
  pushMock.mockReset();
  apiPostMock.mockReset();
});

describe("SearchBox", () => {
  it("renders popular titles and fills the input when clicked", () => {
    render(<SearchBox />);
    fireEvent.click(screen.getByRole("button", { name: "Accountant" }));
    expect(screen.getByLabelText("Enter a job title")).toHaveValue("Accountant");
  });

  it("creates a run and navigates to the run page on submit", async () => {
    apiPostMock.mockResolvedValue({ id: "run-123" });
    render(<SearchBox />);

    fireEvent.change(screen.getByLabelText("Enter a job title"), {
      target: { value: "Data Analyst" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Generate report" }));

    await waitFor(() => expect(apiPostMock).toHaveBeenCalled());
    const [path, body, headers] = apiPostMock.mock.calls[0];
    expect(path).toBe("/api/v1/runs");
    expect(body).toEqual({ job_title: "Data Analyst", filters: {} });
    expect(headers).toHaveProperty("Idempotency-Key");
    await waitFor(() => expect(pushMock).toHaveBeenCalledWith("/runs/run-123"));
  });

  it("shows an error when the API is unreachable", async () => {
    apiPostMock.mockRejectedValue(new Error("Could not start"));
    render(<SearchBox />);

    fireEvent.change(screen.getByLabelText("Enter a job title"), {
      target: { value: "Data Analyst" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Generate report" }));

    await waitFor(() => expect(screen.getByText("Could not start")).toBeInTheDocument());
    expect(pushMock).not.toHaveBeenCalled();
  });

  it("does not submit queries shorter than 2 characters", () => {
    render(<SearchBox />);
    fireEvent.change(screen.getByLabelText("Enter a job title"), { target: { value: "A" } });
    expect(screen.getByRole("button", { name: "Generate report" })).toBeDisabled();
    expect(apiPostMock).not.toHaveBeenCalled();
  });
});
