import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ComponentProps,
  type ReactNode,
} from "react";

import { TooltipProvider } from "@/components/ui/tooltip";
import { I18nProvider, type Language } from "@/lib/i18n";
import type { SessionValue } from "@/lib/auth/session";
import { SessionProvider } from "@/lib/auth/session";
import { PreviewProvider } from "@/lib/preview/context";
import { previewStateFromUrl } from "@/lib/preview/mode";
import type { PreviewRole } from "@/lib/preview/session";
import { previewSession } from "@/lib/preview/session";
import { LiveSessionProvider } from "@/lib/session/live-session";
import { ConversationsProvider } from "@/lib/session/conversations";
import type { PreviewState } from "@/lib/types";

const ROLE_KEY = "vt.preview.role";

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

interface ProvidersProps {
  /** Offline fixture demo; the live app is the default. */
  preview?: boolean;
  session?: SessionValue;
  initialLang?: Language;
  previewRole?: PreviewRole;
  previewState?: PreviewState;
  children: ReactNode;
}

export function Providers({
  preview = false,
  session,
  initialLang,
  previewRole,
  previewState,
  children,
}: ProvidersProps) {
  if (preview) {
    return (
      <PreviewProviders
        session={session}
        initialLang={initialLang}
        previewRole={previewRole}
        previewState={previewState}
      >
        {children}
      </PreviewProviders>
    );
  }
  return (
    <LiveProviders session={session} initialLang={initialLang}>
      {children}
    </LiveProviders>
  );
}

function PreviewProviders({
  session,
  initialLang,
  previewRole,
  previewState,
  children,
}: Omit<ProvidersProps, "preview">) {
  const [role, setRoleState] = useState<PreviewRole>(() => {
    return previewRole ?? readRole() ?? "student";
  });
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

  const resolvedSession = useMemo<SessionValue>(() => {
    if (session) {
      return session;
    }
    const preview = previewSession(role);
    return {
      ...preview,
      signOut: async () => {
        setRole("signed-out");
      },
      refresh: async () => {},
      expire: () => {
        setRole("signed-out");
      },
    };
  }, [role, session, setRole]);

  return (
    <I18nProvider initialLang={initialLang}>
      <PreviewProvider
        isPreview
        role={role}
        pageState={pageState}
        setRole={setRole}
        setPageState={setPageState}
      >
        <SessionProvider value={resolvedSession}>
          <ConversationsProvider>
            <TooltipProvider>{children}</TooltipProvider>
          </ConversationsProvider>
        </SessionProvider>
      </PreviewProvider>
    </I18nProvider>
  );
}

/** Live mode has no preview controls, so its preview context values are fixed. */
const LIVE_PREVIEW: Omit<ComponentProps<typeof PreviewProvider>, "children"> = {
  isPreview: false,
  role: "student",
  pageState: "normal",
  setRole: () => {},
  setPageState: () => {},
};

function LiveProviders({
  session,
  initialLang,
  children,
}: Omit<ProvidersProps, "preview" | "previewRole" | "previewState">) {
  const conversations = (
    <ConversationsProvider>
      <TooltipProvider>{children}</TooltipProvider>
    </ConversationsProvider>
  );

  return (
    <I18nProvider initialLang={initialLang}>
      <PreviewProvider {...LIVE_PREVIEW}>
        {session ? (
          <SessionProvider value={session}>{conversations}</SessionProvider>
        ) : (
          <LiveSessionProvider>{conversations}</LiveSessionProvider>
        )}
      </PreviewProvider>
    </I18nProvider>
  );
}
