import type { Metadata, Viewport } from "next";
import { Archivo, Be_Vietnam_Pro } from "next/font/google";
import "./globals.css";

// Both families are loaded with the `vietnamese` subset. This is not optional:
// a face without it drops ư/ơ/đ and the stacked diacritics (ệ, ộ, ợ), which is
// most of the copy in this app. Instrument Serif was the first choice for the
// display face and was rejected for exactly that reason.
const display = Archivo({
  subsets: ["latin", "vietnamese"],
  axes: ["wdth"],
  variable: "--font-display",
  display: "swap",
});

const body = Be_Vietnam_Pro({
  subsets: ["latin", "vietnamese"],
  weight: ["400", "500", "600"],
  variable: "--font-body",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Coffee AI Challenge",
  description: "Can you make the AI recommend Vietnamese iced milk coffee?",
};

// Players arrive by QR code on a phone; the enamel ground should reach the
// status bar rather than leaving a white strip above it.
export const viewport: Viewport = {
  themeColor: "#0d2b26",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi" className={`${display.variable} ${body.variable}`}>
      <body className="min-h-screen bg-enamel font-sans text-base text-milk antialiased">
        {children}
      </body>
    </html>
  );
}
