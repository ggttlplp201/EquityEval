import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "EquityEval · Sector Explorer",
  description: "Source-aware sector research and comparison. Development data is explicitly fictional.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
