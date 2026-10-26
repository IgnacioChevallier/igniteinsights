"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { authClient } from "@/lib/auth-client";

const INPUT =
  "h-9 rounded-md border border-input bg-background px-3 text-sm font-normal shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring";

export function CuentaForm() {
  const [mensaje, setMensaje] = useState<{ ok: boolean; texto: string } | null>(null);

  const cambiar = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formEl = event.currentTarget;
    const form = new FormData(formEl);
    const nueva = String(form.get("nueva"));
    if (nueva !== String(form.get("repetida"))) {
      setMensaje({ ok: false, texto: "Las contraseñas nuevas no coinciden." });
      return;
    }
    const { error } = await authClient.changePassword({
      currentPassword: String(form.get("actual")),
      newPassword: nueva,
      revokeOtherSessions: true,
    });
    if (error) {
      setMensaje({ ok: false, texto: error.message ?? "No se pudo cambiar la contraseña." });
      return;
    }
    formEl.reset();
    setMensaje({ ok: true, texto: "Contraseña actualizada. Se cerraron las otras sesiones." });
  };

  const salir = async () => {
    await authClient.signOut();
    window.location.assign("/login");
  };

  return (
    <>
      <form onSubmit={cambiar} className="mt-8 flex flex-col gap-3 rounded-lg border p-5">
        <h2 className="font-medium">Cambiar contraseña</h2>
        <label className="flex flex-col gap-1 text-sm">
          Contraseña actual
          <input name="actual" type="password" autoComplete="current-password" required className={INPUT} />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Contraseña nueva (mínimo 10 caracteres)
          <input name="nueva" type="password" autoComplete="new-password" minLength={10} required className={INPUT} />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Repetir la contraseña nueva
          <input name="repetida" type="password" autoComplete="new-password" minLength={10} required className={INPUT} />
        </label>
        {mensaje && (
          <p role="status" className={mensaje.ok ? "text-sm text-emerald-700" : "text-sm text-destructive"}>
            {mensaje.texto}
          </p>
        )}
        <Button type="submit">Guardar</Button>
      </form>
      <Button variant="outline" className="mt-6 w-full" onClick={salir}>
        Cerrar sesión
      </Button>
    </>
  );
}
