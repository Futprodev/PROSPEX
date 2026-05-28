/**
 * Multi-company support. Server components call getActiveCompanyId() inside
 * an async context to learn which company's data to fetch. The active company
 * is stored in a cookie by the client-side CompanySwitcher.
 *
 * If no cookie is set, falls back to NEXT_PUBLIC_COMPANY_ID (single-company
 * default for fresh installs).
 */

// Server-only: this module imports next/headers and must never be bundled
// into a client component. Shared constants live in ./company-constants.
import { cookies } from "next/headers";
import { ACTIVE_COMPANY_COOKIE } from "./company-constants";

export { ACTIVE_COMPANY_COOKIE };

/** Read the active company id from a cookie (server component only). */
export async function getActiveCompanyId(): Promise<string> {
  try {
    const store = await cookies();
    const fromCookie = store.get(ACTIVE_COMPANY_COOKIE)?.value;
    if (fromCookie) return fromCookie;
  } catch {
    // cookies() throws in non-request contexts — fall through to env
  }
  return process.env.NEXT_PUBLIC_COMPANY_ID ?? "";
}
