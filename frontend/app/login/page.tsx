"use client";

import { useState, type FormEvent } from "react";
import { LoaderCircle } from "lucide-react";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import { authClient } from "@/lib/auth-client";

/** Accounts are handed out, not requested: there is no sign-up link on purpose. */
export default function LoginPage() {
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setPending(true);
    setError(null);
    const { error: failure } = await authClient.signIn.email({
      email: String(form.get("email")),
      password: String(form.get("password")),
    });
    if (failure) {
      setError("Email o contraseña incorrectos.");
      setPending(false);
      return;
    }
    // A document navigation, so the middleware sees the new session cookie.
    const next = new URLSearchParams(window.location.search).get("next");
    window.location.assign(next?.startsWith("/") ? next : "/");
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-muted/40 px-4 py-10">
      <div className="flex w-full max-w-sm flex-col items-center gap-8">
        <div className="flex flex-col items-center gap-4 text-center">
          <Image
            src="/images/igniteinsights-celdas.svg"
            alt=""
            aria-hidden="true"
            width={144}
            height={144}
            className="h-28 w-28 sm:h-36 sm:w-36"
          />
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">IgniteInsights</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Pronóstico de propagación de incendios · Patagonia andina
            </p>
          </div>
        </div>

        <form
          onSubmit={submit}
          className="flex w-full flex-col gap-4 rounded-lg border bg-background p-6 shadow-sm"
        >
          <label className="flex flex-col gap-1.5 text-sm font-medium">
            Email
            <input
              name="email"
              type="email"
              autoComplete="email"
              required
              className="h-9 rounded-md border border-input bg-background px-3 text-sm font-normal shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            />
          </label>
          <label className="flex flex-col gap-1.5 text-sm font-medium">
            Contraseña
            <input
              name="password"
              type="password"
              autoComplete="current-password"
              required
              className="h-9 rounded-md border border-input bg-background px-3 text-sm font-normal shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            />
          </label>
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
          <Button type="submit" disabled={pending} className="gap-2">
            {pending && <LoaderCircle className="h-4 w-4 animate-spin" />}
            Ingresar
          </Button>
          <p className="text-center text-xs text-muted-foreground">
            Las cuentas las entrega el equipo de IgniteInsights.
          </p>
        </form>
      </div>
    </main>
  );
}
