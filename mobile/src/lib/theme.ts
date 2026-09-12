import { useColorScheme } from "react-native";

export const light = {
  ground: "#EDF0F4",
  surface: "#FFFFFF",
  surface2: "#F5F7FA",
  ink: "#151B26",
  ink2: "#3B4453",
  muted: "#5F6978",
  faint: "#8B94A3",
  line: "#D8DEE7",
  line2: "#E8ECF1",
  accent: "#2B4C7E",
  accentInk: "#FFFFFF",
  accentSoft: "#E3EAF5",
  gain: "#0E7C55",
  loss: "#C2312E",
  warn: "#B3640A",
  gainSoft: "#E1F3EA",
  lossSoft: "#FBE5E4",
  warnSoft: "#FBEEDB",
  chipL: 36,
  chipBgL: 93,
  chipS: 52,
  dark: false,
};

export const dark: typeof light = {
  ground: "#0D1117",
  surface: "#161C25",
  surface2: "#1C232E",
  ink: "#E8EBF0",
  ink2: "#C4CAD4",
  muted: "#98A2B3",
  faint: "#6E7887",
  line: "#2A3240",
  line2: "#222935",
  accent: "#8FB0E3",
  accentInk: "#0D1117",
  accentSoft: "#1E2B40",
  gain: "#3FCB8E",
  loss: "#F0736E",
  warn: "#E9A24A",
  gainSoft: "#12301F",
  lossSoft: "#3A1B1A",
  warnSoft: "#3A2A12",
  chipL: 72,
  chipBgL: 18,
  chipS: 45,
  dark: true,
};

export type Tokens = typeof light;

export function useTokens(): Tokens {
  const scheme = useColorScheme();
  return scheme === "dark" ? dark : light;
}

export const fonts = {
  serif: "Newsreader_500Medium",
  serifBold: "Newsreader_600SemiBold",
  sans: "InstrumentSans_400Regular",
  sansMedium: "InstrumentSans_500Medium",
  sansSemi: "InstrumentSans_600SemiBold",
  sansBold: "InstrumentSans_700Bold",
  mono: "IBMPlexMono_400Regular",
  monoMedium: "IBMPlexMono_500Medium",
};

export function hsl(h: number, s: number, l: number): string {
  return `hsl(${h}, ${s}%, ${l}%)`;
}

export function moveColor(t: Tokens, v: number | null | undefined): string {
  if (v == null) return t.muted;
  return v > 0.0001 ? t.gain : v < -0.0001 ? t.loss : t.muted;
}
