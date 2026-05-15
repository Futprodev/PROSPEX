import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Link from "next/link";
import { ThemeProvider } from "@/components/theme-provider";
import { ThemeToggle } from "@/components/theme-toggle";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
});

export const metadata: Metadata = {
  title: "PROSPEX",
  description:
    "Financial and regulatory briefing platform for Dutch FinTech SMEs",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <body
        className="min-h-full flex flex-col bg-background text-foreground"
        suppressHydrationWarning
      >
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <header className="border-b sticky top-0 z-10 bg-background/95 backdrop-blur">
            <div className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between">
              <div className="flex items-center gap-8">
                <Link href="/" className="font-bold text-sm tracking-tight">
                  PROSPEX
                </Link>
                <nav className="flex items-center gap-6">
                  <Link
                    href="/"
                    className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                  >
                    Dashboard
                  </Link>
                  <Link
                    href="/briefings"
                    className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                  >
                    History
                  </Link>
                </nav>
              </div>
              <ThemeToggle />
            </div>
          </header>

          <main className="flex-1 max-w-6xl mx-auto w-full px-6 py-8">
            {children}
          </main>
        </ThemeProvider>
      </body>
    </html>
  );
}
