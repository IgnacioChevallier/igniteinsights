# Visual checks for the fire progression animation

The suite runs without FastAPI or ELMFIRE: Playwright starts `stub-api.mjs` and Next.js,
then stops both when it finishes. The stub serves the same envelopes the FastAPI app does
for the handful of endpoints the UI touches, and the specs stub basemap tiles so screenshots
never depend on a tile server being reachable.

Every page needs a session (`middleware.ts`), so the suite needs Postgres for Better Auth.
From the repository root, the supported command starts a disposable database on port 5433,
applies migrations, creates or resets an isolated `e2e@igniteinsights.local` admin, and runs
all specs. It never writes users or sessions to the normal development database:

```bash
make test-e2e
```

`e2e/auth.setup.ts` signs in once and every spec reuses the cookie. Set `E2E_EMAIL` and
`E2E_PASSWORD` only when intentionally using a different disposable account.

```bash
npm run test:e2e:list            # discovery only; does not need Postgres
npm run test:e2e                 # if the migrated database is already running
```

Screenshots land in `../playwright-screenshots/`.

If the environment ships its own chromium (a CI image usually pins a build that does not
match the one this Playwright version would download), point at it instead of running
`playwright install`:

```bash
CHROMIUM_PATH=/opt/pw-browsers/chromium-1194/chrome-linux/chrome npx playwright test
```
