import { NextResponse, type NextRequest } from "next/server";

const API_BASE = process.env.API_BASE_URL ?? "http://localhost:8000";

export async function GET(req: NextRequest) {
  const res = await fetch(`${API_BASE}/api/v1/fuels/map${req.nextUrl.search}`, {
    cache: "no-store",
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
