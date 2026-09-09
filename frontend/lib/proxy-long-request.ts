import http from "node:http";
import https from "node:https";

/**
 * Proxy a POST that can legitimately take many minutes.
 *
 * Node's global `fetch` is undici, which gives up after 300 s of waiting for response
 * headers. A real ingestion measured 452 s: the browser sat on "Ingestando datos…" while
 * the backend finished the work, and the simulation it produced was never shown. These
 * endpoints are synchronous by design — ingestion downloads FIRMS and GFS, derives every
 * raster, and only then answers; ELMFIRE runs to completion before /simulations/run
 * returns — so the proxy has to be willing to wait.
 *
 * `node:http` has no such default and needs no dependency to say so.
 *
 * ponytail: a synchronous multi-minute request is fragile whatever the timeout — a reload
 * loses it. The durable fix is an async job with polling, which is a backend change.
 */
export function postLong(
  url: string,
  body: string,
): Promise<{ status: number; text: string }> {
  const target = new URL(url);
  const client = target.protocol === "https:" ? https : http;

  return new Promise((resolve, reject) => {
    const req = client.request(
      target,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Content-Length": Buffer.byteLength(body),
        },
      },
      (res) => {
        let text = "";
        res.setEncoding("utf8");
        res.on("data", (chunk) => (text += chunk));
        res.on("end", () => resolve({ status: res.statusCode ?? 502, text }));
      },
    );
    req.on("error", reject);
    req.setTimeout(0); // explicit: the wait is the point
    req.write(body);
    req.end();
  });
}

/** The envelope shape every one of these endpoints answers with. */
export function jsonResponse(status: number, text: string) {
  return new Response(text, {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
