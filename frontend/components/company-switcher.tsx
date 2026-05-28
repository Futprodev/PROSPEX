"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ChevronDown, Check, Building2 } from "lucide-react";
import { listCompanies, type CompanyListItem } from "@/lib/api";
import { ACTIVE_COMPANY_COOKIE } from "@/lib/company-constants";

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie
    .split("; ")
    .find((r) => r.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.split("=")[1]) : null;
}

function writeCookie(name: string, value: string) {
  // 365-day cookie scoped to the site root
  const expires = new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toUTCString();
  document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires}; path=/; SameSite=Lax`;
}

export function CompanySwitcher() {
  const [companies, setCompanies] = useState<CompanyListItem[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const router = useRouter();

  useEffect(() => {
    listCompanies().then((list) => setCompanies(list));
    const fromCookie = readCookie(ACTIVE_COMPANY_COOKIE);
    setActiveId(
      fromCookie ?? process.env.NEXT_PUBLIC_COMPANY_ID ?? null
    );
  }, []);

  function selectCompany(id: string) {
    writeCookie(ACTIVE_COMPANY_COOKIE, id);
    setActiveId(id);
    setOpen(false);
    router.refresh();
  }

  // Hide the switcher entirely until we have ≥2 companies — no point in a dropdown of one
  if (companies.length < 2) return null;

  const active = companies.find((c) => c.id === activeId);

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-2 text-sm px-2.5 py-1.5 rounded-md border hover:bg-muted/40 transition-colors"
      >
        <Building2 className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="max-w-[140px] truncate">
          {active?.name ?? "Select company"}
        </span>
        <ChevronDown className="h-3 w-3 text-muted-foreground" />
      </button>

      {open && (
        <>
          {/* Backdrop to close on outside click */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => setOpen(false)}
          />
          <div className="absolute right-0 mt-1 min-w-[220px] z-50 border rounded-md bg-background shadow-md overflow-hidden">
            {companies.map((c) => (
              <button
                key={c.id}
                onClick={() => selectCompany(c.id)}
                className="w-full flex items-center justify-between gap-3 px-3 py-2 text-sm hover:bg-muted/60 transition-colors text-left"
              >
                <span className="flex flex-col">
                  <span className="truncate">{c.name}</span>
                  {c.industry && (
                    <span className="text-xs text-muted-foreground capitalize">
                      {c.industry} · {c.country}
                    </span>
                  )}
                </span>
                {c.id === activeId && (
                  <Check className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                )}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
