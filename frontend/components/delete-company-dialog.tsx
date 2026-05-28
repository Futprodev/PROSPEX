"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { AlertTriangle } from "lucide-react";
import { deleteCompany } from "@/lib/api";
import { ACTIVE_COMPANY_COOKIE } from "@/lib/company-constants";

interface Props {
  companyId:   string;
  companyName: string;
  open:        boolean;
  onClose:     () => void;
}

function clearCookie(name: string) {
  document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:01 GMT; path=/; SameSite=Lax`;
}

export function DeleteCompanyDialog({ companyId, companyName, open, onClose }: Props) {
  const [typed, setTyped]   = useState("");
  const [busy, setBusy]     = useState(false);
  const [error, setError]   = useState<string | null>(null);
  const router = useRouter();

  // Reset state when reopened
  useEffect(() => {
    if (open) {
      setTyped("");
      setBusy(false);
      setError(null);
    }
  }, [open]);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  const canDelete = typed === companyName && !busy;

  async function handleDelete() {
    setBusy(true);
    setError(null);
    const ok = await deleteCompany(companyId);
    if (!ok) {
      setBusy(false);
      setError("Delete failed. Check the backend logs.");
      return;
    }
    clearCookie(ACTIVE_COMPANY_COOKIE);
    onClose();
    // Force a hard navigation so the cookie removal takes effect and the
    // dashboard re-renders with no active company
    router.refresh();
    window.location.href = "/";
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={busy ? undefined : onClose}
      />

      {/* Dialog */}
      <div className="relative bg-background border rounded-xl shadow-xl max-w-md w-full mx-4 p-6 space-y-4">
        <div className="flex items-start gap-3">
          <div className="h-9 w-9 rounded-full bg-red-50 dark:bg-red-950/40 flex items-center justify-center shrink-0">
            <AlertTriangle className="h-5 w-5 text-red-600" />
          </div>
          <div className="space-y-1">
            <h2 className="text-base font-semibold">Delete this company?</h2>
            <p className="text-sm text-muted-foreground">
              This permanently removes <strong className="text-foreground">{companyName}</strong>{" "}
              along with all its briefings and financial snapshots. This cannot
              be undone.
            </p>
          </div>
        </div>

        <div className="space-y-2 pt-1">
          <label className="text-xs text-muted-foreground">
            Type <code className="bg-muted px-1 py-0.5 rounded text-foreground">{companyName}</code> to confirm
          </label>
          <input
            type="text"
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
            disabled={busy}
            autoFocus
            className="w-full px-3 py-2 text-sm border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-red-500/30 focus:border-red-500"
            placeholder={companyName}
          />
        </div>

        {error && (
          <p className="text-xs text-red-500">{error}</p>
        )}

        <div className="flex items-center justify-end gap-2 pt-2">
          <Button variant="ghost" size="sm" onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button
            size="sm"
            onClick={handleDelete}
            disabled={!canDelete}
            className="bg-red-600 hover:bg-red-700 text-white disabled:bg-red-600/40"
          >
            {busy ? "Deleting…" : "Delete company"}
          </Button>
        </div>
      </div>
    </div>
  );
}
