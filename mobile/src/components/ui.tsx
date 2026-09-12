import { Pressable, StyleSheet, Text, View, type StyleProp, type TextStyle, type ViewStyle } from "react-native";

import { fonts, hsl, useTokens } from "@/lib/theme";
import { sectionOf } from "@/lib/sections";

export function Eyebrow({ children, style }: { children: React.ReactNode; style?: StyleProp<TextStyle> }) {
  const t = useTokens();
  return <Text style={[{ fontFamily: fonts.sansSemi, fontSize: 11, letterSpacing: 1, textTransform: "uppercase", color: t.muted }, style]}>{children}</Text>;
}

export function SectionTag({ id }: { id: string }) {
  const t = useTokens();
  const s = sectionOf(id);
  return (
    <View style={{ backgroundColor: hsl(s.hue, 40, t.chipBgL), paddingHorizontal: 8, paddingVertical: 2, borderRadius: 999 }}>
      <Text style={{ fontFamily: fonts.sansSemi, fontSize: 11, color: hsl(s.hue, t.chipS, t.chipL), letterSpacing: 0.3 }}>{s.label}</Text>
    </View>
  );
}

export function Segmented<T extends string>({ value, options, onChange }: { value: T; options: { value: T; label: string }[]; onChange: (v: T) => void }) {
  const t = useTokens();
  return (
    <View style={{ flexDirection: "row", backgroundColor: t.surface2, borderRadius: 999, padding: 3, gap: 2 }}>
      {options.map((o) => {
        const on = o.value === value;
        return (
          <Pressable key={o.value} onPress={() => onChange(o.value)} accessibilityRole="button" accessibilityState={{ selected: on }}
            style={{ paddingHorizontal: 12, paddingVertical: 6, borderRadius: 999, backgroundColor: on ? t.surface : "transparent", ...(on ? shadow : {}) }}>
            <Text style={{ fontFamily: fonts.sansMedium, fontSize: 13, color: on ? t.ink : t.muted }}>{o.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

export function Chip({ label, count, hue, on, onPress }: { label: string; count?: number; hue?: number; on: boolean; onPress: () => void }) {
  const t = useTokens();
  return (
    <Pressable onPress={onPress} accessibilityRole="button" accessibilityState={{ selected: on }}
      style={{ flexDirection: "row", alignItems: "center", gap: 6, paddingHorizontal: 12, paddingVertical: 7, borderRadius: 999, borderWidth: 1,
        borderColor: on ? t.ink : t.line, backgroundColor: on ? t.ink : t.surface }}>
      {hue != null && <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: hsl(hue, t.chipS, t.chipL) }} />}
      <Text style={{ fontFamily: fonts.sansMedium, fontSize: 13, color: on ? t.surface : t.ink2 }}>{label}</Text>
      {count != null && count > 0 && <Text style={{ fontFamily: fonts.mono, fontSize: 11, color: on ? t.surface : t.faint, opacity: on ? 0.7 : 1 }}>{count}</Text>}
    </Pressable>
  );
}

export function Button({ label, onPress, ghost, style }: { label: string; onPress: () => void; ghost?: boolean; style?: StyleProp<ViewStyle> }) {
  const t = useTokens();
  return (
    <Pressable onPress={onPress} accessibilityRole="button"
      style={({ pressed }) => [{ paddingHorizontal: 14, paddingVertical: 10, borderRadius: 9, backgroundColor: ghost ? t.surface2 : t.accent, opacity: pressed ? 0.8 : 1 }, style]}>
      <Text style={{ fontFamily: fonts.sansSemi, fontSize: 14, color: ghost ? t.ink : t.accentInk }}>{label}</Text>
    </Pressable>
  );
}

export function Empty({ title, body }: { title: string; body: string }) {
  const t = useTokens();
  return (
    <View style={{ paddingVertical: 36, paddingHorizontal: 8, alignItems: "center" }}>
      <Text style={{ fontFamily: fonts.serif, fontSize: 20, color: t.ink, marginBottom: 6, textAlign: "center" }}>{title}</Text>
      <Text style={{ fontFamily: fonts.sans, fontSize: 14, color: t.muted, textAlign: "center", maxWidth: 320 }}>{body}</Text>
    </View>
  );
}

export function SectionHead({ title, sub }: { title: string; sub?: string }) {
  const t = useTokens();
  return (
    <View style={{ flexDirection: "row", alignItems: "baseline", justifyContent: "space-between", gap: 12, marginTop: 22, marginBottom: 10 }}>
      <Text style={{ fontFamily: fonts.serifBold, fontSize: 22, color: t.ink, flexShrink: 1 }}>{title}</Text>
      {!!sub && <Text style={{ fontFamily: fonts.sans, fontSize: 12.5, color: t.muted }}>{sub}</Text>}
    </View>
  );
}

export const shadow = StyleSheet.create({
  s: { shadowColor: "#000", shadowOpacity: 0.12, shadowRadius: 3, shadowOffset: { width: 0, height: 1 }, elevation: 1 },
}).s;
