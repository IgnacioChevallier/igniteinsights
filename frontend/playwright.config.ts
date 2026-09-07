import { defineConfig, devices } from "@playwright/test";

/**
 * Visual checks for the map animation. The dev server must already be running against a
 * backend (real, or the stub described in e2e/README.md) on API_BASE_URL.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 60_000,
  use: {
    ...devices["Desktop Chrome"],
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    viewport: { width: 1440, height: 900 },
  },
  projects: [
    {
      name: "chromium",
      use: {
        // Honour a chromium supplied by the environment (CI images pin their own build,
        // which need not match the one this Playwright version would download).
        launchOptions: process.env.CHROMIUM_PATH
          ? { executablePath: process.env.CHROMIUM_PATH }
          : {},
      },
    },
  ],
});
