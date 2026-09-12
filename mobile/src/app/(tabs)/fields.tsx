import { useRouter } from "expo-router";
import { useMemo } from "react";
import { Pressable, ScrollView, Text, View } from "react-native";

import { SectionHead } from "@/components/ui";
import { useDesk } from "@/lib/data";
import { SECTIONS } from "@/lib/sections";
import { fonts, hsl, useTokens } from "@/lib/theme";

export default function FieldsScreen() {
  const t = useTokens();
  const router = useRouter();
  const { data } = useDesk();
  const by = useMemo(() => {
    const m: Record<string, { n: number; top?: string }> = {};
    for (const a of data?.feed.articles ?? []) {
      m[a.section] = m[a.section] ?? { n: 0, top: a.title };
      m[a.section].n += 1;
    }
    return m;
  }, [data]);

  return (
    <ScrollView contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 24 }}>
      <SectionHead title="Browse by field" sub={data ? `${data.feed.articles.length} stories today` : undefined} />
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 10, marginTop: 4 }}>
        {SECTIONS.map((s) => {
          const info = by[s.id];
          return (
            <Pressable key={s.id} onPress={() => router.push({ pathname: "/field/[id]", params: { id: s.id } })}
              style={({ pressed }) => ({ width: "48%", flexGrow: 1, minHeight: 96, backgroundColor: t.surface2, borderRadius: 12, borderTopWidth: 3, borderTopColor: hsl(s.hue, t.chipS, t.chipL), paddingHorizontal: 14, paddingTop: 14, paddingBottom: 12, opacity: pressed ? 0.7 : 1 })}>
              <Text style={{ fontFamily: fonts.sansSemi, fontSize: 15, color: t.ink }}>{s.label}</Text>
              <Text style={{ fontFamily: fonts.mono, fontSize: 12, color: t.muted, marginTop: 4 }}>{info ? `${info.n} stor${info.n === 1 ? "y" : "ies"}` : "…"}</Text>
              <Text numberOfLines={2} style={{ fontFamily: fonts.sans, fontSize: 12.5, color: t.muted, marginTop: 6, lineHeight: 17 }}>{info?.top ?? s.blurb}</Text>
            </Pressable>
          );
        })}
      </View>
    </ScrollView>
  );
}
