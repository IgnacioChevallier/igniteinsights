import { request, type FullConfig } from "@playwright/test";
import { betterAuth } from "better-auth";
import { admin } from "better-auth/plugins";
import pg from "pg";

/**
 * Every page is behind a session now (middleware.ts), and the specs drive the admin
 * dashboard. Sign in once as the admin named by E2E_EMAIL / E2E_PASSWORD and hand the cookie
 * to every test. Better Auth needs Postgres even when the API is the stub (README.md).
 */
export const STORAGE_STATE = "e2e/.auth.json";
export const E2E_EMAIL = process.env.E2E_EMAIL ?? "e2e@igniteinsights.local";
export const E2E_PASSWORD = process.env.E2E_PASSWORD ?? "e2e-password-local";

async function ensureAdmin(email: string, password: string, baseURL: string) {
  const pool = new pg.Pool({
    connectionString:
      process.env.DATABASE_URL ??
      "postgresql://igniteinsights:igniteinsights@localhost:5433/igniteinsights",
  });
  const auth = betterAuth({
    baseURL,
    secret:
      process.env.BETTER_AUTH_SECRET ??
      "Qq7vF4mN9xL2sK8wC5rT1yH6uJ3pD0bG7zA4eS9nM2cV8fR1",
    database: pool,
    emailAndPassword: { enabled: true, disableSignUp: true, minPasswordLength: 10 },
    plugins: [admin()],
  });

  try {
    const ctx = await auth.$context;
    const existing = await ctx.internalAdapter.findUserByEmail(email);
    if (existing) {
      await ctx.internalAdapter.updatePassword(existing.user.id, await ctx.password.hash(password));
      await ctx.internalAdapter.deleteUserSessions(existing.user.id);
      await pool.query('update "user" set role = $1 where id = $2', ["admin", existing.user.id]);
    } else {
      await auth.api.createUser({
        body: { email, password, name: "E2E", role: "admin" },
      });
    }
  } finally {
    await pool.end();
  }
}

export default async function globalSetup(config: FullConfig) {
  const baseURL = config.projects[0].use.baseURL!;
  const email = E2E_EMAIL;
  const password = E2E_PASSWORD;
  await ensureAdmin(email, password, baseURL);
  const context = await request.newContext({ baseURL, extraHTTPHeaders: { origin: baseURL } });
  const res = await context.post("/api/auth/sign-in/email", { data: { email, password } });
  if (!res.ok()) throw new Error(`E2E sign-in failed: HTTP ${res.status()} ${await res.text()}`);
  await context.storageState({ path: STORAGE_STATE });
  await context.dispose();
}
