import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "JPM Digital — Markets",
  description: "Digital markets overview and stablecoin metrics (data via RWA.xyz API when configured).",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">
        <header className="border-b border-[var(--border)] bg-[var(--card)]/80 backdrop-blur">
          <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4">
            <Link href="/" className="text-lg font-semibold tracking-tight text-white">
              JPM Digital
            </Link>
            <nav className="flex gap-4 text-sm text-zinc-400">
              <Link href="/" className="hover:text-white">
                Home
              </Link>
              <Link href="/crypto-etps" className="hover:text-white">
                Crypto ETPs
              </Link>
              <Link href="/stablecoins" className="hover:text-white">
                Stablecoins
              </Link>
              <Link href="/tokenized-stocks" className="hover:text-white">
                Tokenized Stocks
              </Link>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-4 py-10">{children}</main>
      </body>
    </html>
  );
}
