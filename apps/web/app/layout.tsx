import type { Metadata, Viewport } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import { esMX } from "@clerk/localizations";
import Providers from "./providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "NidoGuard",
  description: "Mejor vida. Más valor.",
  manifest: "/manifest.webmanifest",
};
export const viewport: Viewport = { themeColor: "#183b56", width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider localization={esMX}>
      <html lang="es-MX">
        <body>
          <Providers>{children}</Providers>
        </body>
      </html>
    </ClerkProvider>
  );
}
