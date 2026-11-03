import { useCallback, useEffect, useState, type ReactNode } from "react";

import { TooltipProvider } from "@/components/ui/tooltip";
import { I18nProvider, type Language } from "@/lib/i18n";
import type { SessionValue } from "@/lib/auth/session";
import { SessionProvider } from "@/lib/auth/session";
import { PreviewProvider } from "@/lib/preview/context";
import type { PreviewRole } from "@/lib/preview/session";
import { previewSession } from "@/lib/preview/session";
import type { PreviewState } from "@/lib/types";

const ROLE_KEY = "vt.preview.role";

function previewStateFromUrl(): PreviewState {
  if (typeof window === "undefined") {
    return "normal";
  }
  const value = new URLSearchParams(window.location.search).get("preview");
  return value === "loading" || value === "empty" || value === "error"
    ? value
    : "normal";
}

function readRole(): PreviewRole | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    const fromUrl = new URLSearchParams(window.location.search).get("previewRole");
    if (fromUrl === "student" || fromUrl === "instructor" || fromUrl === "signed-out") {
      return fromUrl;
    }
    const stored = window.localStorage?.getItem(ROLE_KEY);
    if (stored === "student" || stored === "instructor" || stored === "signed-out") {
      return stored;
    }
  } catch {
    // Storage can be blocked; fall through to the default role.
  }
  return null;
}

function storeRole(role: PreviewRole): void {
  try {
    window.localStorage?.setItem(ROLE_KEY, role);
  } catch {
    // The in-memory choice still applies.
  }
}

export function Providers({
  session,
  initialLang,
  previewRole,
  previewState,
  children,
}: {
  session?: SessionValue;
  initialLang?: Language;
  previewRole?: PreviewRole;
  previewState?: PreviewState;
  children: ReactNode;
}) {
  const [role, setRoleState] = useState<PreviewRole>(
    () => previewRole ?? readRole() ?? "student",
  );
  const [pageState, setPageState] = useState<PreviewState>(
    () => previewState ?? previewStateFromUrl(),
  );

  const setRole = useCallback((next: PreviewRole) => {
    setRoleState(next);
    storeRole(next);
  }, []);

  useEffect(() => {
    storeRole(role);
  }, [role]);

  const previewEnabled = import.meta.env.VITE_PREVIEW !== "0";
  const resolvedSession: SessionValue =
    session ??
    (previewEnabled
      ? { ...previewSession(role), signOut: () => setRole("signed-out") }
      : { status: "anonymous", user: null, signOut: () => {} });

  return (
    <I18nProvider initialLang={initialLang}>
      <PreviewProvider
        isPreview={previewEnabled}
        role={role}
        pageState={pageState}
        setRole={setRole}
        setPageState={setPageState}
      >
        <SessionProvider value={resolvedSession}>
          <TooltipProvider>{children}</TooltipProvider>
        </SessionProvider>
      </PreviewProvider>
    </I18nProvider>
  );
}
