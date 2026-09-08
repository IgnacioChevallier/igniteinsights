# Visual checks for the fire progression animation

The animation is frontend-only, so these run without Python or ELMFIRE: `stub-api.mjs`
serves the same envelopes the FastAPI app does for the handful of endpoints the map
touches, and the spec stubs the basemap tiles so a screenshot never depends on a tile
server being reachable.

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
