import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { AppState } from "react-native";

import { DeskContext, fetchDesk, loadCachedDesk, REFRESH_MS, type DeskApi } from "./data";
import { DEFAULT_PREFS, loadPrefs, PrefsContext, savePrefs, type Prefs, type PrefsApi } from "./store";
import type { DeskData } from "./types";

export function DeskProvider({ children }: { children: ReactNode }) {
  const [data, setData] = useState<DeskData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [offline, setOffline] = useState(false);
  const inFlight = useRef<Promise<void> | null>(null);

  const refresh = useCallback(async () => {
    if (inFlight.current) return inFlight.current;
    const p = (async () => {
      try {
        const fresh = await fetchDesk();
        setData(fresh);
        setError(null);
        setOffline(false);
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
        setOffline(true);
      } finally {
        setLoading(false);
        inFlight.current = null;
      }
    })();
    inFlight.current = p;
    return p;
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const cached = await loadCachedDesk();
      if (cached && !cancelled) {
        setData(cached);
        setLoading(false);
      }
      await refresh();
    })();
    const timer = setInterval(refresh, REFRESH_MS);
    const sub = AppState.addEventListener("change", (s) => {
      if (s === "active") refresh();
    });
    return () => {
      cancelled = true;
      clearInterval(timer);
      sub.remove();
    };
  }, [refresh]);

  const index = useMemo(() => {
    const m = new Map<string, DeskData["feed"]["articles"][number]>();
    data?.feed.articles.forEach((a) => m.set(a.id, a));
    return m;
  }, [data]);

  const api = useMemo<DeskApi>(
    () => ({ data, loading, error, offline, refresh, byId: (id) => index.get(id) }),
    [data, loading, error, offline, refresh, index],
  );
  return <DeskContext.Provider value={api}>{children}</DeskContext.Provider>;
}

export function PrefsProvider({ children }: { children: ReactNode }) {
  const [prefs, setPrefs] = useState<Prefs>(DEFAULT_PREFS);
  const loaded = useRef(false);

  useEffect(() => {
    loadPrefs().then((p) => {
      setPrefs(p);
      loaded.current = true;
    });
  }, []);

  useEffect(() => {
    if (loaded.current) savePrefs(prefs);
  }, [prefs]);

  useEffect(() => {
    const sub = AppState.addEventListener("change", (s) => {
      if (s !== "active") setPrefs((p) => ({ ...p, lastSeen: Date.now() }));
    });
    return () => sub.remove();
  }, []);

  const api = useMemo<PrefsApi>(
    () => ({
      prefs,
      markRead: (id) => setPrefs((p) => (p.read.includes(id) ? p : { ...p, read: [...p.read, id] })),
      toggleSaved: (id) => {
        const now = prefs.saved.includes(id);
        setPrefs((p) => ({ ...p, saved: now ? p.saved.filter((x) => x !== id) : [id, ...p.saved] }));
        return !now;
      },
      setRegion: (region) => setPrefs((p) => ({ ...p, region })),
      setSort: (sort) => setPrefs((p) => ({ ...p, sort })),
      touchLastSeen: () => setPrefs((p) => ({ ...p, lastSeen: Date.now() })),
      isRead: (id) => prefs.read.includes(id),
      isSaved: (id) => prefs.saved.includes(id),
    }),
    [prefs],
  );
  return <PrefsContext.Provider value={api}>{children}</PrefsContext.Provider>;
}
