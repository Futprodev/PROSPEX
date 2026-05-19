"use client";

import { Button } from "@/components/ui/button";
import { Printer } from "lucide-react";

export function PrintButton() {
  return (
    <Button
      onClick={() => window.print()}
      variant="outline"
      size="sm"
      className="no-print"
    >
      <Printer className="h-3.5 w-3.5 mr-1.5" />
      Export PDF
    </Button>
  );
}
