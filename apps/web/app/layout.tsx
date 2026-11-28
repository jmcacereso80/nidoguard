import type { Metadata, Viewport } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import { esMX } from "@clerk/localizations";
import Providers from "./providers";
import { clerkAppearance } from "@/lib/clerkAppearance";
import "./globals.css";

export const metadata: Metadata = {
  title: "NidoGuard",
  description: "Mejor vida. Más valor.",
  manifest: "/manifest.webmanifest",
};
export const viewport: Viewport = { themeColor: "#183b56", width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider localization={esMX} appearance={clerkAppearance}>
      {/* suppressHydrationWarning: extensiones del navegador (p. ej. Chrome) agregan atributos a <html> antes de hidratar. */}
      <html lang="es-MX" suppressHydrationWarning>
        <body>
          <Providers>{children}</Providers>
        </body>
      </html>
    </ClerkProvider>
  );
}
