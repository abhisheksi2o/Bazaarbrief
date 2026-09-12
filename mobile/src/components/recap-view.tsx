import { useRouter } from "expo-router";
import { Pressable, Text, View } from "react-native";

import { Eyebrow } from "@/components/ui";
import { useDesk } from "@/lib/data";
import { pct } from "@/lib/format";
import { fonts, moveColor, useTokens } from "@/lib/theme";
import type { Daily, ScoreEntry, Weekly } from "@/lib/types";

function Scoreboard({ entries }: { entries?: ScoreEntry[] }) {
  const t = useTokens();
  if (!entries?.length) return null;
  return (
    <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 14 }}>
      {entries.map((e) => (
        <View key={e.label} style={{ width: "31%", flexGrow: 1, backgroundColor: t.surface2, borderRadius: 8, paddingHorizontal: 10, paddingVertical: 8 }}>
          <Text numberOfLines={1} style={{ fontFamily: fonts.sans, fontSize: 11, color: t.muted }}>{e.label}</Text>
          <Text style={{ fontFamily: fonts.mono, fontSize: 13, color: t.ink, fontVariant: ["tabular-nums"] }}>{e.value}</Text>
          <Text style={{ fontFamily: fonts.mono, fontSize: 11.5, color: moveColor(t, e.changePct ?? (e.change?.startsWith("+") ? 1 : e.change?.startsWith("-") ? -1 : 0)), fontVariant: ["tabular-nums"] }}>
            {e.changePct != null ? pct(e.changePct) : e.change ?? ""}
          </Text>
        </View>
      ))}
    </View>
  );
}

export function RecapView({ doc, kind }: { doc: Daily | Weekly; kind: "day" | "week" }) {
  const t = useTokens();
  const router = useRouter();
  const { byId } = useDesk();
  const eyebrow = kind === "day"
    ? `${(doc as Daily).sessionLabel ?? "Recap of the day"} · ${(doc as Daily).dateLabel ?? (doc as Daily).date}`
    : `Recap of the week · ${(doc as Weekly).rangeLabel ?? (doc as Weekly).week}`;
  return (
    <View>
      <View style={{ paddingTop: 18, paddingBottom: 12, borderBottomWidth: 1, borderBottomColor: t.line }}>
        <View style={{ flexDirection: "row", justifyContent: "space-between", flexWrap: "wrap", gap: 10 }}>
          <Eyebrow>{eyebrow}</Eyebrow>
          <Eyebrow>{doc.readMinutes ?? (kind === "day" ? 3 : 4)} min read</Eyebrow>
        </View>
        <Text style={{ fontFamily: fonts.serifBold, fontSize: 28, lineHeight: 33, color: t.ink, marginTop: 8, marginBottom: 8 }}>{doc.title}</Text>
        {!!doc.standfirst && <Text style={{ fontFamily: fonts.sans, fontSize: 16, lineHeight: 24, color: t.ink2 }}>{doc.standfirst}</Text>}
        <Scoreboard entries={doc.scoreboard} />
      </View>
      {(doc.groups ?? []).map((g) => (
        <View key={g.label} style={{ marginTop: 18 }}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 6 }}>
            <Eyebrow>{g.label}</Eyebrow>
            <View style={{ flex: 1, height: 1, backgroundColor: t.line2 }} />
          </View>
          {g.items.map((it, i) => {
            const link = (it.ids ?? []).find((id) => byId(id));
            return (
              <View key={i} style={{ paddingVertical: 8, borderBottomWidth: i < g.items.length - 1 ? 1 : 0, borderBottomColor: t.line2 }}>
                <Text style={{ fontFamily: fonts.sans, fontSize: 15, lineHeight: 22, color: t.ink }}>
                  {it.text}
                  {link ? "  " : ""}
                  {link && (
                    <Text onPress={() => router.push({ pathname: "/story/[id]", params: { id: link } })} style={{ fontFamily: fonts.sansSemi, fontSize: 12, color: t.accent }}>
                      Open story
                    </Text>
                  )}
                </Text>
              </View>
            );
          })}
        </View>
      ))}
      {!!doc.watch?.length && (
        <View style={{ marginTop: 18, backgroundColor: t.accentSoft, borderRadius: 12, paddingHorizontal: 16, paddingVertical: 14 }}>
          <Eyebrow style={{ color: t.accent, marginBottom: 6 }}>{kind === "day" ? "What to watch next" : "The week ahead"}</Eyebrow>
          {doc.watch.map((w, i) => (
            <View key={i} style={{ flexDirection: "row", gap: 8, marginVertical: 3 }}>
              <Text style={{ color: t.ink, fontFamily: fonts.sans, fontSize: 14.5 }}>•</Text>
              <Text style={{ flex: 1, color: t.ink, fontFamily: fonts.sans, fontSize: 14.5, lineHeight: 21 }}>{w}</Text>
            </View>
          ))}
        </View>
      )}
    </View>
  );
}

export function DateStrip<T extends { key: string; label: string }>({ items, active, onSelect }: { items: T[]; active: string; onSelect: (k: string) => void }) {
  const t = useTokens();
  return (
    <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 6, paddingTop: 12 }}>
      {items.map((d) => {
        const on = d.key === active;
        return (
          <Pressable key={d.key} onPress={() => onSelect(d.key)} style={{ paddingHorizontal: 10, paddingVertical: 6, borderRadius: 8, backgroundColor: on ? t.ink : t.surface2 }}>
            <Text style={{ fontFamily: fonts.sansMedium, fontSize: 12.5, color: on ? t.surface : t.muted, fontVariant: ["tabular-nums"] }}>{d.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}
