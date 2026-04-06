"use client";

import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { getMe, logout, refresh, type User } from "@/lib/api";

type SessionState =
  | { status: "loading"; user: null }
  | { status: "authenticated"; user: User }
  | { status: "unauthenticated"; user: null };

type SessionContextValue = {
  state: SessionState;
  reload: () => Promise<void>;
  logout: () => Promise<void>;
};

const SessionContext = createContext<SessionContextValue | null>(null);

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<SessionState>({ status: "loading", user: null });

  const reload = useCallback(async () => {
    setState({ status: "loading", user: null });
    try {
      const user = await getMe();
      setState({ status: "authenticated", user });
    } catch {
      try {
        await refresh();
        const user = await getMe();
        setState({ status: "authenticated", user });
      } catch {
        setState({ status: "unauthenticated", user: null });
      }
    }
  }, []);

  const doLogout = useCallback(async () => {
    await logout();
    setState({ status: "unauthenticated", user: null });
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void reload();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [reload]);

  const value = useMemo(() => ({ state, reload, logout: doLogout }), [state, reload, doLogout]);

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession() {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSession must be used within SessionProvider");
  return ctx;
}

