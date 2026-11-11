import { defineConfig, devices } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { STORAGE_STATE } from "./e2e/auth.setup";

mkdirSync(fileURLToPath(new URL("../outputs/playwright/current/", import.meta.url)), {
  recursive: true,
});

const baseURL = process.env.E2E_BASE_URL ?? "http://localhost:3000";
const databaseURL =
  process.env.DATABASE_URL ??
  "postgresql://igniteinsights:igniteinsights@127.0.0.1:5433/igniteinsights";

/**
 * Visual checks for the map animation. The dev server must already be running against a
 * backend (real, or the stub described in e2e/README.md) on API_BASE_URL.
 */
export default defineConfig({
  testDir: "./e2e",
  globalSetup: "./e2e/auth.setup.ts",
  fullyParallel: false,
  workers: 1,
  timeout: 60_000,
  webServer: [
    {
      command: "node e2e/stub-api.mjs",
      port: 8000,
      reuseExistingServer: !process.env.CI,
    },
    {
      command: "npm run dev",
      url: `${baseURL}/login`,
      reuseExistingServer: !process.env.CI,
      env: {
        ...process.env,
        API_BASE_URL: "http://localhost:8000",
        BETTER_AUTH_SECRET:
          process.env.BETTER_AUTH_SECRET ??
          "Qq7vF4mN9xL2sK8wC5rT1yH6uJ3pD0bG7zA4eS9nM2cV8fR1",
        BETTER_AUTH_URL: baseURL,
        DATABASE_URL: databaseURL,
      },
    },
  ],
  use: {
    ...devices["Desktop Chrome"],
    baseURL,
    storageState: STORAGE_STATE,
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
