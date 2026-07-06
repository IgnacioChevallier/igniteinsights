import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { DashboardShell } from "@/components/dashboard-shell";
import type { DashboardData } from "@/lib/dashboard-types";

type DashboardEnvelope = {
  status: string;
  data: DashboardData;
  error: { message?: string } | null;
  meta: { timestamp: string };
};

async function getDashboardData() {
  const apiBaseUrl = process.env.API_BASE_URL ?? "http://localhost:8000";

  try {
    const response = await fetch(`${apiBaseUrl}/api/v1/dashboard/summary`, {
      cache: "no-store",
    });

    if (!response.ok) {
      return {
        apiBaseUrl,
        data: null,
        error: `La API devolvió ${response.status}`,
      };
    }

    const envelope = (await response.json()) as DashboardEnvelope;
    return { apiBaseUrl, data: envelope.data, error: null };
  } catch (error) {
    return {
      apiBaseUrl,
      data: null,
      error: error instanceof Error ? error.message : "No se pudo conectar con la API",
    };
  }
}

export default async function DashboardPage() {
  const { apiBaseUrl, data, error } = await getDashboardData();

  if (error || !data) {
    return (
      <main className="mx-auto flex min-h-screen max-w-6xl items-center justify-center p-6">
        <Card className="w-full max-w-xl">
          <CardHeader>
            <CardTitle>Panel</CardTitle>
            <CardDescription>API no disponible en {apiBaseUrl}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Badge variant="destructive">{error ?? "Error desconocido"}</Badge>
            <form>
              <Button type="submit" variant="outline" size="sm">
                Actualizar
              </Button>
            </form>
          </CardContent>
        </Card>
      </main>
    );
  }

  return <DashboardShell data={data} apiBaseUrl={apiBaseUrl} />;
}
