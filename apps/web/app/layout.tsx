import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DeepScout — Research with evidence",
  description: "A focused, source-backed research brief.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
