import { expect, test } from "@playwright/test";

test("landing page shows hero, search, and popular titles", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "What does the Qatari job market actually ask for?" }),
  ).toBeVisible();
  await expect(page.getByLabel("Enter a job title")).toBeVisible();
  await expect(page.getByRole("button", { name: "AI Engineer" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Generate report" })).toBeVisible();
});

test("typing a popular title fills the search input", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Accountant" }).click();
  await expect(page.getByLabel("Enter a job title")).toHaveValue("Accountant");
});

test("unknown report page still has share metadata and an error state", async ({ page }) => {
  await page.goto("/reports/00000000-0000-0000-0000-000000000000");
  await expect(page).toHaveTitle(/ResearchFlow AI/);
  await expect(page.getByRole("heading", { name: "Report unavailable" })).toBeVisible();
  await expect(page.locator('meta[name="twitter:card"]')).toHaveAttribute("content", "summary");
});

test("jobs and about pages render", async ({ page }) => {
  await page.goto("/jobs");
  await expect(page.getByLabel(/search/i).first()).toBeVisible();

  await page.goto("/about");
  await expect(page.getByRole("heading").first()).toBeVisible();
});
