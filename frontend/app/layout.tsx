import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Ignite Insights",
  description: "Panel de lectura para ejecuciones y entradas ELMFIRE de Ignite Insights",
  icons: {
    icon: "/images/wildfire-logo-tree-colored.svg",
    shortcut: "/images/wildfire-logo-tree-colored.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
