import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NerdCommand.AI — JARVIS",
  description: "Personal AI command system — one interface, many specialists.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
