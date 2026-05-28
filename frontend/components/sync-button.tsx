"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { syncXero } from "@/lib/api";

interface Props {
  companyId: string;
}

export function SyncButton({ companyId }: Props) {
  const [state, setState] = useState<"idle" | "loading" | "waiting">("idle");
  const router = useRouter();

  async function handleClick() {
    setState("loading");
    const ok = await syncXero(companyId);
    if (!ok) {
      setState("idle");
      return;
    }
    setState("waiting");
    // Xero pull typically finishes in ~10s. Refresh after 15s.
    setTimeout(() => {
      router.refresh();
      setState("idle");
    }, 15_000);
  }

  if (state === "loading") {
    return (
      <Button variant="ghost" disabled size="sm">
        <span className="inline-block animate-spin mr-2">⟳</span>
        Syncing…
      </Button>
    );
  }

  if (state === "waiting") {
    return (
      <Button variant="ghost" disabled size="sm">
        Pulling Xero — refreshing in ~15s
      </Button>
    );
  }

  return (
    <Button onClick={handleClick} variant="ghost" size="sm">
      ↓ Sync Xero
    </Button>
  );
}
