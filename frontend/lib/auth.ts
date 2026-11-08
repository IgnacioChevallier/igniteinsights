import { betterAuth } from "better-auth";
import { nextCookies } from "better-auth/next-js";
import { admin } from "better-auth/plugins";
import { Pool } from "pg";

/**
 * Users and sessions for the product (docs/producto.md §4).
 *
 * Two roles from the admin plugin: "admin" sees everything the dashboard had before, "user"
 * (shown as "cliente") only sees the map, the documentation and their account. Nobody can
 * sign up: accounts are created with `npm run usuarios -- crear …` (scripts/usuarios.ts).
 * The tables live in the same Postgres as the API, created by alembic 0006.
 */
export const auth = betterAuth({
  database: new Pool({ connectionString: process.env.DATABASE_URL }),
  emailAndPassword: { enabled: true, disableSignUp: true, minPasswordLength: 10 },
  session: {
    cookieCache: { enabled: true, maxAge: 5 * 60 },
  },
  plugins: [admin(), nextCookies()],
});

export type Session = typeof auth.$Infer.Session;

export const isAdmin = (session: Session | null) => session?.user.role === "admin";
