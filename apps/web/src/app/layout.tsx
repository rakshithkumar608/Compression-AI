import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "EcoCompress AI — Reproducible Model Compression Benchmark",
  description: "Evidence-based AI model compression evaluation with real latency, memory, quality, and energy benchmarks.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-[#0b0f19] text-slate-100 antialiased">
        {children}
      </body>
    </html>
  );
}
