import AsyncStorage from "@react-native-async-storage/async-storage";
import { createContext, useContext } from "react";

import type { Archive, Article, DeskData, Feed, Markets, PaperIndex } from "./types";

/** The desk publishes plain JSON files here (GitHub Pages, rebuilt once a day at 06:00 IST). */
export const SITE_BASE = "https://abhisheksi2o.github.io/Bazaarbrief/";
export const DATA_BASE = SITE_BASE + "data/";
export const PAPER_BASE = SITE_BASE + "paper/";
export const REFRESH_MS = 60 * 60 * 1000;
const CACHE_KEY = "bb:desk";

async function getJson<T>(name: string): Promise<T> {
  const bust = Math.floor(Date.now() / 60000);
  const res = await fetch(`${DATA_BASE}${name}?t=${bust}`, { headers: { "Cache-Control": "no-cache" } });
  if (!res.ok) throw new Error(`${name} ${res.status}`);
  return (await res.json()) as T;
}

export async function fetchDesk(): Promise<DeskData> {
  const [feed, markets, archive, paper] = await Promise.all([
    getJson<Feed>("feed.json"),
    getJson<Markets>("markets.json"),
    getJson<Archive>("archive.json").catch(() => ({ dailies: [], weeklies: [] }) as Archive),
    fetch(`${PAPER_BASE}index.json?t=${Math.floor(Date.now() / 60000)}`).then((r) => (r.ok ? (r.json() as Promise<PaperIndex>) : null)).catch(() => null),
  ]);
  const data: DeskData = { feed, markets, archive: normalizeArchive(archive), paper, fetchedAt: Date.now() };
  AsyncStorage.setItem(CACHE_KEY, JSON.stringify(data)).catch(() => {});
  return data;
}

export async function loadCachedDesk(): Promise<DeskData | null> {
  try {
    const raw = await AsyncStorage.getItem(CACHE_KEY);
    return raw ? (JSON.parse(raw) as DeskData) : null;
  } catch {
    return null;
  }
}

function normalizeArchive(a: Archive): Archive {
  return {
    updatedAt: a.updatedAt,
    dailies: [...(a.dailies ?? [])].sort((x, y) => (y.date ?? "").localeCompare(x.date ?? "")).slice(0, 14),
    weeklies: [...(a.weeklies ?? [])].sort((x, y) => (y.week ?? "").localeCompare(x.week ?? "")).slice(0, 8),
  };
}

export interface DeskApi {
  data: DeskData | null;
  loading: boolean;
  error: string | null;
  offline: boolean;
  refresh(): Promise<void>;
  byId(id: string): Article | undefined;
}

export const DeskContext = createContext<DeskApi | null>(null);

export function useDesk(): DeskApi {
  const v = useContext(DeskContext);
  if (!v) throw new Error("DeskContext missing");
  return v;
}

export function feedAgeHours(data: DeskData | null): number | null {
  if (!data) return null;
  const t = Date.parse(data.feed.updatedAt);
  return t ? (Date.now() - t) / 3600000 : null;
}
