/**
 * Accounts are handed out, not requested (docs/dashboard-producto.md §9).
 *
 *   DATABASE_URL=postgres://… npm run usuarios -- crear jurado1@ejemplo.com "Nombre Apellido" [cliente|admin]
 *   DATABASE_URL=postgres://… npm run usuarios -- resetear jurado1@ejemplo.com
 *   DATABASE_URL=postgres://… npm run usuarios -- listar
 *
 * Prints a random initial password to hand over; the user changes it under "Cuenta". Runs on
 * Node's own TypeScript support (node ≥ 22.18), so it builds its own Better Auth instance with
 * the same database and plugin as lib/auth.ts rather than importing the Next-bound one.
 */
import { randomBytes } from "node:crypto";
import { betterAuth } from "better-auth";
import { admin } from "better-auth/plugins";
import pg from "pg";

const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL });
const auth = betterAuth({
  database: pool,
  emailAndPassword: { enabled: true, disableSignUp: true, minPasswordLength: 10 },
  plugins: [admin()],
});

const password = () => randomBytes(9).toString("base64url");
const [command, email, name, rol = "cliente"] = process.argv.slice(2);

async function main() {
  if (command === "crear" && email && name) {
    const role = rol === "admin" ? "admin" : "user";
    const pass = password();
    await auth.api.createUser({ body: { email, password: pass, name, role } });
    console.log(`Creado ${email} (${role === "admin" ? "admin" : "cliente"}). Contraseña inicial: ${pass}`);
  } else if (command === "resetear" && email) {
    const ctx = await auth.$context;
    const user = await ctx.internalAdapter.findUserByEmail(email);
    if (!user) throw new Error(`No existe ${email}`);
    const pass = password();
    await ctx.internalAdapter.updatePassword(user.user.id, await ctx.password.hash(pass));
    await ctx.internalAdapter.deleteUserSessions(user.user.id);
    console.log(`Nueva contraseña de ${email}: ${pass} (sus sesiones se cerraron)`);
  } else if (command === "listar") {
    const { rows } = await pool.query('select email, name, role, "createdAt" from "user" order by "createdAt"');
    for (const r of rows) console.log(`${r.email}\t${r.role === "admin" ? "admin" : "cliente"}\t${r.name}`);
  } else {
    console.error('Uso: npm run usuarios -- crear <email> "<nombre>" [cliente|admin] | resetear <email> | listar');
    process.exitCode = 2;
  }
}

main()
  .catch((e) => {
    console.error(e instanceof Error ? e.message : e);
    process.exitCode = 1;
  })
  .finally(() => pool.end());
