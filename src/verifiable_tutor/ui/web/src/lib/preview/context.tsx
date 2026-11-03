import { createContext, useContext, type ReactNode } from "react";

import type { PreviewState } from "@/lib/types";
import type { PreviewRole } from "@/lib/preview/session";

interface PreviewValue {
  isPreview: boolean;
  role: PreviewRole;
  pageState: PreviewState;
  setRole: (role: PreviewRole) => void;
  setPageState: (state: PreviewState) => void;
}

const PreviewContext = createContext<PreviewValue | null>(null);

export function PreviewProvider({
  isPreview = true,
  role,
  pageState,
  setRole,
  setPageState,
  children,
}: {
  isPreview?: boolean;
  role: PreviewRole;
  pageState: PreviewState;
  setRole: (role: PreviewRole) => void;
  setPageState: (state: PreviewState) => void;
  children: ReactNode;
}) {
  return (
    <PreviewContext.Provider
      value={{ isPreview, role, pageState, setRole, setPageState }}
    >
      {children}
    </PreviewContext.Provider>
  );
}

export function usePreview(): PreviewValue {
  const value = useContext(PreviewContext);
  if (value === null) {
    throw new Error("usePreview must be used inside PreviewProvider");
  }
  return value;
}
