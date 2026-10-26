import { headers } from "next/headers";
import { ClientHeader } from "@/components/client-header";
import { CuentaForm } from "@/components/cuenta-form";
import { auth } from "@/lib/auth";

export default async function CuentaPage() {
  const session = await auth.api.getSession({ headers: await headers() });
  const user = session?.user;
  return (
    <div className="flex min-h-screen flex-col">
      <ClientHeader active="cuenta" isAdmin={user?.role === "admin"} />
      <main className="mx-auto w-full max-w-md px-4 py-8">
        <h1 className="text-xl font-semibold">Cuenta</h1>
        <dl className="mt-4 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
          <dt className="text-muted-foreground">Nombre</dt>
          <dd>{user?.name}</dd>
          <dt className="text-muted-foreground">Email</dt>
          <dd>{user?.email}</dd>
          <dt className="text-muted-foreground">Rol</dt>
          <dd>{user?.role === "admin" ? "Administrador" : "Cliente"}</dd>
        </dl>
        <CuentaForm />
      </main>
    </div>
  );
}
