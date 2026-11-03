import { createContext, useContext, type ReactNode } from "react";

import type { Me } from "@/lib/types";

export type SessionStatus = "loading" | "authenticated" | "anonymous";

export interface SessionValue {
  status: SessionStatus;
  user: Me | null;
  signOut: () => void;
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
