import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Link from "next/link";
import { ThemeProvider } from "@/components/theme-provider";
import { ThemeToggle } from "@/components/theme-toggle";
import { CompanyMenu } from "@/components/company-menu";
import { TaskProgressProvider } from "@/components/task-progress-provider";
import { ProgressBanner } from "@/components/progress-banner";
import { AgentChat } from "@/components/agent-chat";
import { getCompany } from "@/lib/api";
import { getActiveCompanyId } from "@/lib/company";
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

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  // Resolve the active company once at the layout level so the header menu
  // and the dashboard share a single source of truth.
  const companyId = await getActiveCompanyId();
  const company   = companyId ? await getCompany(companyId) : null;

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
         <TaskProgressProvider>
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
                    href="/briefing"
                    className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                  >
                    Briefing
                  </Link>
                  <Link
                    href="/financials"
                    className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                  >
                    Financials
                  </Link>
                  <Link
                    href="/briefings"
                    className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                  >
                    History
                  </Link>
                </nav>
              </div>
              <div className="flex items-center gap-2">
                {company && (
                  <CompanyMenu
                    companyId={company.id}
                    companyName={company.name}
                    industry={company.industry}
                    country={company.country}
                  />
                )}
                <ThemeToggle />
              </div>
            </div>
          </header>

          <ProgressBanner />

          <main className="flex-1 max-w-6xl mx-auto w-full px-6 py-8">
            {children}
          </main>

          {/* Floating chat — appears bottom-right whenever a company is connected */}
          {company && <AgentChat companyId={company.id} />}
         </TaskProgressProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
