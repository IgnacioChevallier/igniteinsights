import { NextResponse } from "next/server";

const API_BASE = process.env.API_BASE_URL ?? "http://localhost:8000";

export async function GET(request: Request) {
  const params = new URL(request.url).searchParams;
  const harness = params.get("harness");
  const caso = params.get("caso");
  const mapa = params.get("mapa");
  if (!harness || !caso || !mapa) {
    return NextResponse.json({ detail: "faltan harness, caso o mapa" }, { status: 400 });
  }
  const res = await fetch(
    `${API_BASE}/api/v1/validation/cases/${harness}/${caso}/overlay?mapa=${mapa}`,
    { cache: "no-store" },
  );
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
