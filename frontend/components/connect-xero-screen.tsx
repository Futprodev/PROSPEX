"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { getXeroAuthUrl } from "@/lib/api";

/**
 * Shown when no company is connected (no cookie + no matching company in the
 * backend). Single CTA that runs the OAuth flow; the callback creates the row
 * and sets the active-company cookie so when the user lands back here the
 * dashboard renders with their data.
 */
export function ConnectXeroScreen() {
  const [busy, setBusy] = useState(false);

  async function handleConnect() {
    setBusy(true);
    const url = await getXeroAuthUrl(); // no company_id → "new" mode
    if (!url) {
      setBusy(false);
      alert("Could not start Xero connect. Check the backend logs.");
      return;
    }
    // Navigate in the same tab — Xero redirects back to FRONTEND_URL after auth
    window.location.href = url;
  }

  return (
    <div className="flex flex-col items-center justify-center py-24 text-center gap-6 max-w-md mx-auto">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">
          Connect your Xero account
        </h1>
        <p className="text-sm text-muted-foreground">
          PROSPEX needs read-only access to your Xero data to generate weekly
          financial briefings. You can disconnect any time.
        </p>
      </div>

      <Button
        size="lg"
        onClick={handleConnect}
        disabled={busy}
        className="px-6"
      >
        {busy ? "Opening Xero…" : "Connect Xero"}
      </Button>

      <div className="text-xs text-muted-foreground space-y-1">
        <p>What we read:</p>
        <p>Profit &amp; Loss · Balance Sheet · Aged Receivables · Bank Transactions</p>
      </div>
    </div>
  );
}
