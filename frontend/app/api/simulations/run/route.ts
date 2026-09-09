import type { NextRequest } from "next/server";
import { jsonResponse, postLong } from "@/lib/proxy-long-request";

const API_BASE = process.env.API_BASE_URL ?? "http://localhost:8000";

// Slow on purpose: this endpoint answers only once the work is done, well past the 300 s
// at which Node's fetch would have given up. See lib/proxy-long-request.
export async function POST(req: NextRequest) {
  const { status, text } = await postLong(`${API_BASE}/api/v1/simulations/run`, await req.text());
  return jsonResponse(status, text);
}
