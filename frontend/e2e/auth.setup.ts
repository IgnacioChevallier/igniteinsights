import { request, type FullConfig } from "@playwright/test";

/**
 * Every page is behind a session now (middleware.ts), and the specs drive the admin
 * dashboard. Sign in once as the admin named by E2E_EMAIL / E2E_PASSWORD and hand the cookie
 * to every test. Better Auth needs Postgres even when the API is the stub (README.md).
 */
export const STORAGE_STATE = "e2e/.auth.json";

export default async function globalSetup(config: FullConfig) {
  const baseURL = config.projects[0].use.baseURL!;
  const { E2E_EMAIL: email, E2E_PASSWORD: password } = process.env;
  if (!email || !password) {
    throw new Error("Set E2E_EMAIL and E2E_PASSWORD to an admin account (e2e/README.md)");
  }
  const context = await request.newContext({ baseURL, extraHTTPHeaders: { origin: baseURL } });
  const res = await context.post("/api/auth/sign-in/email", { data: { email, password } });
  if (!res.ok()) throw new Error(`E2E sign-in failed: HTTP ${res.status()} ${await res.text()}`);
  await context.storageState({ path: STORAGE_STATE });
  await context.dispose();
}
