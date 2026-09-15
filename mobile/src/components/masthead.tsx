import { useRouter } from "expo-router";
import { Pressable, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { feedAgeHours, useDesk } from "@/lib/data";
import { ago, istDateLabel, num, pct, yieldChange } from "@/lib/format";
import { fonts, moveColor, useTokens } from "@/lib/theme";

const RAIL = ["^NSEI", "^BSESN", "^NSEBANK", "INR=X", "^TNX", "BZ=F", "GC=F", "^GSPC", "^IXIC", "^N225", "BTC-USD", "^INDIAVIX", "DX-Y.NYB"];

export function Masthead() {
  const t = useTokens();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { data, offline, loading } = useDesk();
  const age = feedAgeHours(data);
  const dot = !data ? t.faint : age != null && age > 30 ? t.warn : t.gain;
  const freshText = !data ? (loading ? "Loading…" : "Offline") : offline ? `Offline · ${ago(data.feed.updatedAt)}` : `Updated ${ago(data.feed.updatedAt)}`;
  const quotes = new Map((data?.markets.quotes ?? []).map((q) => [q.symbol, q]));

  return (
    <View style={{ paddingTop: insets.top, backgroundColor: t.surface, borderBottomWidth: 1, borderBottomColor: t.line }}>
      <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: 16, paddingTop: 10, paddingBottom: 6 }}>
        <View style={{ flexDirection: "row", alignItems: "baseline", gap: 8 }}>
          <Text style={{ fontFamily: fonts.serifBold, fontSize: 24, color: t.ink }}>Bazaar Brief</Text>
          <Text style={{ fontFamily: fonts.sans, fontSize: 12, color: t.muted }}>{istDateLabel()}</Text>
        </View>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
          <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: dot }} />
          <Text style={{ fontFamily: fonts.sans, fontSize: 12, color: t.muted }}>{freshText}</Text>
        </View>
      </View>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ paddingHorizontal: 12, paddingBottom: 10, gap: 6 }}>
        {RAIL.map((sym) => {
          const q = quotes.get(sym);
          const isYield = q?.kind === "yield";
          return (
            <Pressable key={sym} onPress={() => router.push("/markets")} style={{ backgroundColor: t.surface2, borderRadius: 8, paddingHorizontal: 10, paddingVertical: 6, minWidth: 112 }}>
              <Text style={{ fontFamily: fonts.sans, fontSize: 11, color: t.muted }}>{q?.label ?? sym}</Text>
              <Text style={{ fontFamily: fonts.mono, fontSize: 14, color: t.ink, fontVariant: ["tabular-nums"] }}>
                {q && !q.error ? (isYield ? `${q.price.toFixed(3)}%` : num(q.price)) : "—"}
              </Text>
              <Text style={{ fontFamily: fonts.mono, fontSize: 11.5, color: moveColor(t, q?.change), fontVariant: ["tabular-nums"] }}>
                {q && !q.error ? (isYield ? yieldChange(q.change) : pct(q.changePct)) : ""}
              </Text>
            </Pressable>
          );
        })}
      </ScrollView>
    </View>
  );
}
