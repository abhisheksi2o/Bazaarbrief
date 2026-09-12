import AsyncStorage from "@react-native-async-storage/async-storage";
import { createContext, useContext } from "react";

const KEY = "bb:prefs";

export interface Prefs {
  read: string[];
  saved: string[];
  lastSeen: number;
  region: "all" | "india" | "world";
  sort: "top" | "latest";
}

export const DEFAULT_PREFS: Prefs = { read: [], saved: [], lastSeen: 0, region: "all", sort: "top" };

export async function loadPrefs(): Promise<Prefs> {
  try {
    const raw = await AsyncStorage.getItem(KEY);
    if (!raw) return DEFAULT_PREFS;
    return { ...DEFAULT_PREFS, ...(JSON.parse(raw) as Partial<Prefs>) };
  } catch {
    return DEFAULT_PREFS;
  }
}

export async function savePrefs(p: Prefs): Promise<void> {
  try {
    await AsyncStorage.setItem(KEY, JSON.stringify({ ...p, read: p.read.slice(-600) }));
  } catch {
    // storage is a convenience; never block the UI on it
  }
}

export interface PrefsApi {
  prefs: Prefs;
  markRead(id: string): void;
  toggleSaved(id: string): boolean;
  setRegion(r: Prefs["region"]): void;
  setSort(s: Prefs["sort"]): void;
  touchLastSeen(): void;
  isRead(id: string): boolean;
  isSaved(id: string): boolean;
}

export const PrefsContext = createContext<PrefsApi | null>(null);

export function usePrefs(): PrefsApi {
  const v = useContext(PrefsContext);
  if (!v) throw new Error("PrefsContext missing");
  return v;
}
