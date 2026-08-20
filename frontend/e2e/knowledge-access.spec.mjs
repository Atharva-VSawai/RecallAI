import { test, expect } from "@playwright/test";

test("unauthenticated users cannot open knowledge upload", async ({ page }) => {
  await page.goto("/query?tab=upload");
  await expect(page).toHaveURL(/\/login/);
});

test("viewer sees an access explanation instead of a misleading PDF-only uploader", async ({ page }) => {
  test.skip(!process.env.E2E_AUTH_STATE, "Set E2E_AUTH_STATE to a signed-in Viewer storage state.");
  await page.goto("/query?tab=upload");
  await expect(page.getByText("Upload access required")).toBeVisible();
  await expect(page.getByText("Drop your PDF here")).toHaveCount(0);
  await expect(page.getByText("Docs", { exact: true })).toHaveCount(0);
});
