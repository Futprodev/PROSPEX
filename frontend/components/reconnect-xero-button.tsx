"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Link as LinkIcon } from "lucide-react";
import { getXeroAuthUrl } from "@/lib/api";

interface Props {
  companyId: string;
}

export function ReconnectXeroButton({ companyId }: Props) {
  const [busy, setBusy] = useState(false);

  async function handleClick() {
    setBusy(true);
    const url = await getXeroAuthUrl(companyId);
    setBusy(false);
    if (!url) {
      alert("Could not start Xero reconnect. Check the backend logs.");
      return;
    }
    // Open in a new tab so the user keeps the dashboard open
    window.open(url, "_blank", "noopener");
  }

  return (
    <Button
      onClick={handleClick}
      disabled={busy}
      variant="ghost"
      size="sm"
      title="Re-authorise Xero — use this after resetting the Demo Company"
    >
      <LinkIcon className="h-3.5 w-3.5 mr-1.5" />
      {busy ? "Opening…" : "Reconnect Xero"}
    </Button>
  );
}
