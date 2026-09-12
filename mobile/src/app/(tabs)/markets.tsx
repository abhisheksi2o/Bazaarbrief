import { ScrollView, Text, View } from "react-native";

import { Sparkline } from "@/components/sparkline";
import { Empty, Eyebrow, SectionHead } from "@/components/ui";
import { useDesk } from "@/lib/data";
import { ago, num, pct, yieldChange } from "@/lib/format";
import { fonts, moveColor, useTokens } from "@/lib/theme";

const GROUPS: { key: string; label: string }[] = [
  { key: "India", label: "India" }, { key: "FX", label: "Currencies" }, { key: "Rates", label: "Rates" },
  { key: "Commodities", label: "Commodities" }, { key: "World", label: "World" }, { key: "Crypto", label: "Crypto" },
];

export default function MarketsScreen() {
  const t = useTokens();
  const { data } = useDesk();
  const quotes = (data?.markets.quotes ?? []).filter((q) => !q.error);
  return (
    <ScrollView contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 28 }}>
      <SectionHead title="Markets" sub={data ? `as of ${ago(data.markets.updatedAt)}` : undefined} />
      {!quotes.length && <Empty title="No quotes yet" body="Market data arrives with the next desk update." />}
      {GROUPS.map((g) => {
        const rows = quotes.filter((q) => q.group === g.key);
        if (!rows.length) return null;
        return (
          <View key={g.key} style={{ marginTop: 20 }}>
            <Eyebrow style={{ marginBottom: 4 }}>{g.label}</Eyebrow>
            {rows.map((q, i) => {
              const isY = q.kind === "yield";
              return (
                <View key={q.symbol} style={{ flexDirection: "row", alignItems: "center", gap: 8, paddingVertical: 10, borderBottomWidth: i < rows.length - 1 ? 1 : 0, borderBottomColor: t.line2 }}>
                  <View style={{ flex: 1 }}>
                    <Text style={{ fontFamily: fonts.sansMedium, fontSize: 14.5, color: t.ink }}>{q.label}</Text>
                    <Text style={{ fontFamily: fonts.mono, fontSize: 11, color: t.faint }}>{q.symbol}{q.currency && !isY ? ` · ${q.currency}` : ""}</Text>
                  </View>
                  <Text style={{ width: 84, textAlign: "right", fontFamily: fonts.mono, fontSize: 14, color: t.ink, fontVariant: ["tabular-nums"] }}>{isY ? `${q.price.toFixed(3)}%` : num(q.price)}</Text>
                  <View style={{ width: 80, alignItems: "flex-end" }}>
                    <Text style={{ fontFamily: fonts.mono, fontSize: 13, color: moveColor(t, q.change), fontVariant: ["tabular-nums"] }}>{isY ? yieldChange(q.change) : pct(q.changePct)}</Text>
                    <Text style={{ fontFamily: fonts.mono, fontSize: 10, color: t.faint, fontVariant: ["tabular-nums"] }}>5D {pct(q.weekPct)}</Text>
                    <Text style={{ fontFamily: fonts.mono, fontSize: 10, color: t.faint, fontVariant: ["tabular-nums"] }}>1M {pct(q.monthPct)}</Text>
                  </View>
                  <Sparkline values={q.spark} />
                </View>
              );
            })}
          </View>
        );
      })}
      <Text style={{ fontFamily: fonts.sans, fontSize: 12, color: t.muted, marginTop: 16, lineHeight: 17 }}>
        Index levels from exchange data via Yahoo Finance, refreshed with each desk update. 5D and 1M are moves over the last five and roughly twenty-two trading sessions. Sparkline shows the last twelve sessions. Not investment advice.
      </Text>
    </ScrollView>
  );
}
