import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { authApi } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";
import {
  SessionProvider,
  type SessionStatus,
  type SessionValue,
} from "@/lib/auth/session";
import type { Me } from "@/lib/types";

interface SessionState {
  status: SessionStatus;
  user: Me | null;
}

const ANONYMOUS: SessionState = { status: "anonymous", user: null };

/**
 * Live session provider: bootstrap the server session once, then keep the
 * client state in step with login, logout, and expiry.
 *
 * `unavailable` separates "the backend cannot be reached" from "not signed in",
 * so a down backend renders a retry state instead of a login loop.
 */
export function LiveSessionProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<SessionState>({ status: "loading", user: null });
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const refresh = useCallback(async () => {
    setState((current) => ({ ...current, status: "loading" }));
    try {
      const user = await authApi.me();
      if (mounted.current) {
        setState({ status: "authenticated", user });
      }
    } catch (error) {
      if (!mounted.current) {
        return;
      }
      if (error instanceof ApiError && error.status === 401) {
        setState(ANONYMOUS);
      } else {
        setState((current) => ({ ...current, status: "unavailable" }));
      }
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const signOut = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      // The client session is cleared even when the backend call fails.
    }
    if (mounted.current) {
      setState(ANONYMOUS);
    }
  }, []);

  const expire = useCallback(() => {
    if (mounted.current) {
      setState(ANONYMOUS);
    }
  }, []);

  const value = useMemo<SessionValue>(
    () => ({
      status: state.status,
      user: state.user,
      signOut,
      refresh,
      expire,
    }),
    [expire, refresh, signOut, state.status, state.user],
  );

  return <SessionProvider value={value}>{children}</SessionProvider>;
}
