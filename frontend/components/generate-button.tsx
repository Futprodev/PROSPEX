"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { generateBriefing } from "@/lib/api";

interface Props {
  companyId: string;
}

export function GenerateButton({ companyId }: Props) {
  const [state, setState] = useState<"idle" | "loading" | "waiting">("idle");
  const router = useRouter();

  async function handleClick() {
    setState("loading");
    const ok = await generateBriefing(companyId);
    if (!ok) {
      setState("idle");
      return;
    }
    setState("waiting");
    // The pipeline takes ~30 seconds. Refresh the page after 35s.
    setTimeout(() => {
      router.refresh();
      setState("idle");
    }, 35_000);
  }

  if (state === "loading") {
    return (
      <Button variant="outline" disabled size="sm">
        <span className="inline-block animate-spin mr-2">⟳</span>
        Starting…
      </Button>
    );
  }

  if (state === "waiting") {
    return (
      <Button variant="outline" disabled size="sm">
        Generating — refreshing in ~35s
      </Button>
    );
  }

  return (
    <Button onClick={handleClick} variant="outline" size="sm">
      ↻ Generate Briefing
    </Button>
  );
}
