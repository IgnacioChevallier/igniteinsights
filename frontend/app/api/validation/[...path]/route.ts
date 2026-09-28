import { NextRequest, NextResponse } from "next/server";

const API_BASE = process.env.API_BASE_URL ?? "http://localhost:8000";

/** Todo /api/validation/* es de sólo lectura: se reenvía tal cual al backend. */
export async function GET(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params;
  const ruta = path.map(encodeURIComponent).join("/");
  const res = await fetch(`${API_BASE}/api/v1/validation/${ruta}${req.nextUrl.search}`, {
    cache: "no-store",
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
