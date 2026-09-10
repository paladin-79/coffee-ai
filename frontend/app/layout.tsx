import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Coffee AI Challenge",
  description: "Can you make the AI recommend Vietnamese iced milk coffee?",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi">
      <body className="min-h-screen bg-coffee-bg text-coffee-ink antialiased">
        {children}
      </body>
    </html>
  );
}
