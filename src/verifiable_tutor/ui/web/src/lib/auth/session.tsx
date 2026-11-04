import { createContext, useContext, type ReactNode } from "react";

import type { Me } from "@/lib/types";

export type SessionStatus = "loading" | "authenticated" | "anonymous" | "unavailable";

export interface SessionValue {
  status: SessionStatus;
  user: Me | null;
  /** Clear the server session where possible, then the client state. */
  signOut: () => Promise<void>;
  /** Re-read the session (after sign-in, or to retry a failed bootstrap). */
  refresh: () => Promise<void>;
  /** Drop the client session after an unauthorized API response. */
  expire: () => void;
}

const SessionContext = createContext<SessionValue | null>(null);

export function SessionProvider({
  value,
  children,
}: {
  value: SessionValue;
  children: ReactNode;
}) {
  return (
    <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
  );
}

export function useSession(): SessionValue {
  const value = useContext(SessionContext);
  if (value === null) {
    throw new Error("useSession must be used inside SessionProvider");
  }
  return value;
}
