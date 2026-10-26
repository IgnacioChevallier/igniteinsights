import { NextResponse, type NextRequest } from "next/server";
import { auth } from "@/lib/auth";

/**
 * The only gate (docs/dashboard-producto.md §4). The FastAPI service has no public domain
 * and no auth of its own: every browser request reaches it through this app, so this
 * middleware decides who sees what. Deny by default: a "cliente" reaches only the pages
 * and read-only endpoints listed here; an admin reaches everything the dashboard had.
 */
const PUBLIC = [/^\/login$/, /^\/api\/auth\//];

const CLIENT_PAGES = [/^\/$/, /^\/cuenta$/, /^\/documentacion$/];
// GET only. The per-run layers are what the client map draws; terrain feeds the 3D view.
const CLIENT_API = [
  /^\/api\/v1\/operativo\/estado$/,
  /^\/api\/simulations\/[^/]+\/(isochrones|ignition|stats|wind|ensemble-agreement)$/,
  /^\/api\/v1\/terrain\//,
];

const matches = (rules: RegExp[], path: string) => rules.some((rule) => rule.test(path));

export async function middleware(request: NextRequest) {
  const path = request.nextUrl.pathname;
  if (matches(PUBLIC, path)) return NextResponse.next();

  const isApi = path.startsWith("/api/") || path === "/health";
  const session = await auth.api.getSession({ headers: request.headers });
  if (!session) {
    if (isApi) return NextResponse.json({ detail: "No autenticado" }, { status: 401 });
    const login = new URL("/login", request.url);
    if (path !== "/") login.searchParams.set("next", path);
    return NextResponse.redirect(login);
  }
  if (session.user.role === "admin") return NextResponse.next();

  const allowed = isApi
    ? request.method === "GET" && matches(CLIENT_API, path)
    : matches(CLIENT_PAGES, path);
  if (allowed) return NextResponse.next();
  if (isApi) return NextResponse.json({ detail: "Sin permiso" }, { status: 403 });
  return NextResponse.redirect(new URL("/", request.url));
}

export const config = {
  // Node runtime: the session lookup reads Postgres through `pg`.
  runtime: "nodejs",
  matcher: ["/((?!_next/static|_next/image|images/|favicon).*)"],
};
