import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Ignite Insights",
  description: "Panel de lectura para ejecuciones y entradas ELMFIRE de Ignite Insights",
  icons: {
    icon: [
      { url: "/images/igniteinsights-celdas.svg", type: "image/svg+xml" },
      { url: "/images/igniteinsights-celdas.png", type: "image/png" },
    ],
    shortcut: "/images/igniteinsights-celdas.svg",
    // Own file: iOS paints a transparent icon's background black and crops to the edges.
    apple: "/images/apple-touch-icon.png",
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
