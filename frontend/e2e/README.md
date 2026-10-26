# Visual checks for the fire progression animation

The animation is frontend-only, so these run without Python or ELMFIRE: `stub-api.mjs`
serves the same envelopes the FastAPI app does for the handful of endpoints the map
touches, and the spec stubs the basemap tiles so a screenshot never depends on a tile
server being reachable.

Every page needs a session (`middleware.ts`), so the dev server needs Postgres for Better Auth
— the docker-compose `db` is enough, with alembic at head — and an admin to sign in as:

```bash
DATABASE_URL=postgresql://igniteinsights:igniteinsights@localhost:5432/igniteinsights \
  npm run usuarios -- crear e2e@igniteinsights.local "E2E" admin   # prints the password
export E2E_EMAIL=e2e@igniteinsights.local E2E_PASSWORD=<printed password>
```

`e2e/auth.setup.ts` signs in once and every spec reuses the cookie.

```bash
node e2e/stub-api.mjs &          # stands in for the backend on :8000
                                 # PORT=8010 to run it alongside a real backend
npm run dev &                    # Next.js reads API_BASE_URL, default http://localhost:8000
npx playwright test
```

Screenshots land in `../playwright-screenshots/`.

If the environment ships its own chromium (a CI image usually pins a build that does not
match the one this Playwright version would download), point at it instead of running
`playwright install`:

```bash
CHROMIUM_PATH=/opt/pw-browsers/chromium-1194/chrome-linux/chrome npx playwright test
```
