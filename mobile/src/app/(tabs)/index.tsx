import { useRouter } from "expo-router";
import * as WebBrowser from "expo-web-browser";
import { useMemo, useState } from "react";
import { FlatList, Pressable, RefreshControl, ScrollView, Text, TextInput, View } from "react-native";

import { StoryRow } from "@/components/story-row";
import { Button, Chip, Empty, Eyebrow, SectionHead, Segmented } from "@/components/ui";
import { PAPER_BASE, useDesk } from "@/lib/data";
import { SECTIONS, sectionOf } from "@/lib/sections";
import { usePrefs } from "@/lib/store";
import { fonts, useTokens } from "@/lib/theme";
import type { Article } from "@/lib/types";

const PAGE = 30;

export default function TodayScreen() {
  const t = useTokens();
  const router = useRouter();
  const { data, loading, refresh, offline } = useDesk();
  const { prefs, setRegion, setSort, isRead } = usePrefs();
  const [section, setSection] = useState("all");
  const [q, setQ] = useState("");
  const [limit, setLimit] = useState(PAGE);
  const [refreshing, setRefreshing] = useState(false);

  const articles = data?.feed.articles ?? [];
  const counts = useMemo(() => {
    const c: Record<string, number> = {};
    for (const a of articles) if (prefs.region === "all" || a.region === prefs.region) c[a.section] = (c[a.section] ?? 0) + 1;
    return c;
  }, [articles, prefs.region]);

  const items = useMemo(() => {
    let list = articles;
    if (prefs.region !== "all") list = list.filter((a) => a.region === prefs.region);
    if (section !== "all") list = list.filter((a) => a.section === section);
    const needle = q.trim().toLowerCase();
    if (needle) list = list.filter((a) => `${a.title} ${a.summary ?? ""} ${a.source}`.toLowerCase().includes(needle));
    if (prefs.sort === "latest") list = [...list].sort((a, b) => Date.parse(b.publishedAt) - Date.parse(a.publishedAt));
    return list;
  }, [articles, prefs.region, prefs.sort, section, q]);

  const newCount = prefs.lastSeen ? items.filter((a) => Date.parse(a.publishedAt) > prefs.lastSeen && !isRead(a.id)).length : 0;
  const daily = data?.archive.dailies[0];
  const briefBullets = (daily?.groups ?? []).flatMap((g) => g.items.map((i) => i.text)).slice(0, 4);
  const filtered = section !== "all" || prefs.region !== "all" || !!q.trim();
  const base = prefs.sort === "latest" ? "Latest" : "Top stories";
  const title = q.trim() ? "Search results" : section !== "all" ? sectionOf(section).label : prefs.region === "india" ? `${base} · India` : prefs.region === "world" ? `${base} · World` : base;

  const onRefresh = async () => {
    setRefreshing(true);
    await refresh();
    setRefreshing(false);
  };

  const paper = data?.paper?.latest;
  const header = (
    <View>
      {paper && !filtered && (
        <View style={{ marginTop: 14, backgroundColor: "#F6DBCF", borderRadius: 14, borderWidth: 1, borderColor: "#E7C4B4", paddingHorizontal: 14, paddingVertical: 12, flexDirection: "row", gap: 12, alignItems: "center" }}>
          <View style={{ width: 44, height: 60, borderRadius: 3, backgroundColor: "#FBEDE5", borderWidth: 1, borderColor: "#D9B4A3", padding: 5, justifyContent: "space-between" }}>
            <View style={{ height: 6, backgroundColor: "#1B1B1B", borderRadius: 1 }} /><View style={{ height: 3, backgroundColor: "#1B1B1B" }} /><View style={{ height: 3, width: "60%", backgroundColor: "#8A2F1F" }} /><View style={{ height: 3, backgroundColor: "#1B1B1B" }} /><View style={{ height: 3, backgroundColor: "#1B1B1B" }} />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={{ fontFamily: fonts.serifBold, fontSize: 17, color: "#1B1B1B" }}>Today's paper</Text>
            <Text style={{ fontFamily: fonts.sans, fontSize: 12.5, color: "#4a3a34", marginTop: 2, marginBottom: 8 }}>Four pages, edition {paper.number}. Front page, Markets & Money, Economy & Policy, World & Corporate.</Text>
            <View style={{ flexDirection: "row", gap: 8, flexWrap: "wrap" }}>
              <Pressable onPress={() => WebBrowser.openBrowserAsync(PAPER_BASE + "latest.pdf")} style={{ backgroundColor: "#1B1B1B", paddingHorizontal: 12, paddingVertical: 7, borderRadius: 8 }}>
                <Text style={{ fontFamily: fonts.sansSemi, fontSize: 13, color: "#F6DBCF" }}>Read the paper</Text>
              </Pressable>
              <Pressable onPress={() => WebBrowser.openBrowserAsync(PAPER_BASE + paper.file)} style={{ borderWidth: 1, borderColor: "#1B1B1B", paddingHorizontal: 12, paddingVertical: 7, borderRadius: 8 }}>
                <Text style={{ fontFamily: fonts.sansSemi, fontSize: 13, color: "#1B1B1B" }}>Download PDF</Text>
              </Pressable>
            </View>
          </View>
        </View>
      )}
      {daily && !filtered && (
        <View style={{ marginTop: 14, backgroundColor: t.surface2, borderRadius: 14, borderWidth: 1, borderColor: t.line2, paddingHorizontal: 16, paddingTop: 16, paddingBottom: 14 }}>
          <View style={{ flexDirection: "row", justifyContent: "space-between", gap: 10 }}>
            <Eyebrow>{daily.sessionLabel ?? "Daily brief"}</Eyebrow>
            <Eyebrow>{daily.dateLabel ?? daily.date} · {daily.readMinutes ?? 3} min read</Eyebrow>
          </View>
          <Text style={{ fontFamily: fonts.serifBold, fontSize: 23, lineHeight: 28, color: t.ink, marginTop: 8, marginBottom: 6 }}>{daily.title}</Text>
          {!!daily.standfirst && <Text style={{ fontFamily: fonts.sans, fontSize: 14.5, lineHeight: 21, color: t.ink2, marginBottom: 10 }}>{daily.standfirst}</Text>}
          {briefBullets.map((b, i) => (
            <View key={i} style={{ flexDirection: "row", gap: 8, marginVertical: 4 }}>
              <Text style={{ color: t.ink2, fontFamily: fonts.sans, fontSize: 14.5 }}>•</Text>
              <Text style={{ flex: 1, color: t.ink2, fontFamily: fonts.sans, fontSize: 14.5, lineHeight: 21 }}>{b}</Text>
            </View>
          ))}
          <Pressable onPress={() => router.push("/recap")} style={{ marginTop: 10 }}>
            <Text style={{ fontFamily: fonts.sansSemi, fontSize: 13.5, color: t.accent }}>Read the full recap →</Text>
          </Pressable>
        </View>
      )}
      <View style={{ flexDirection: "row", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: 10, marginTop: 14, marginBottom: 6 }}>
        <Segmented value={prefs.region} onChange={(v) => { setRegion(v); setLimit(PAGE); }} options={[{ value: "all", label: "All" }, { value: "india", label: "India" }, { value: "world", label: "World" }]} />
        <Segmented value={prefs.sort} onChange={(v) => { setSort(v); setLimit(PAGE); }} options={[{ value: "top", label: "Top" }, { value: "latest", label: "Latest" }]} />
      </View>
      <View style={{ flexDirection: "row", alignItems: "center", gap: 8, backgroundColor: t.surface2, borderRadius: 10, paddingHorizontal: 12, paddingVertical: 8, marginTop: 6 }}>
        <Text style={{ color: t.faint }}>⌕</Text>
        <TextInput value={q} onChangeText={(v) => { setQ(v); setLimit(PAGE); }} placeholder="Search today's stories" placeholderTextColor={t.faint}
          style={{ flex: 1, fontFamily: fonts.sans, fontSize: 15, color: t.ink, padding: 0 }} autoCorrect={false} clearButtonMode="while-editing" />
      </View>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginHorizontal: -16 }} contentContainerStyle={{ paddingHorizontal: 16, paddingVertical: 10, gap: 6 }}>
        <Chip label="All" count={Object.values(counts).reduce((x, y) => x + y, 0)} on={section === "all"} onPress={() => { setSection("all"); setLimit(PAGE); }} />
        {SECTIONS.map((s) => (
          <Chip key={s.id} label={s.short} hue={s.hue} count={counts[s.id] ?? 0} on={section === s.id} onPress={() => { setSection(s.id); setLimit(PAGE); }} />
        ))}
      </ScrollView>
      <SectionHead title={title} sub={data ? `${items.length} stor${items.length === 1 ? "y" : "ies"}${newCount ? ` · ${newCount} new` : ""}` : undefined} />
      {offline && data && <Text style={{ fontFamily: fonts.sans, fontSize: 12, color: t.warn, marginBottom: 6 }}>You're offline. Showing the last edition saved on this phone.</Text>}
    </View>
  );

  return (
    <FlatList<Article>
      data={data ? items.slice(0, limit) : []}
      keyExtractor={(a) => a.id}
      renderItem={({ item, index }) => <StoryRow article={item} lead={index === 0 && !q.trim()} />}
      ListHeaderComponent={header}
      ListEmptyComponent={
        loading && !data ? <Empty title="Opening the desk…" body="Fetching today's stories and market data." />
        : !data ? <Empty title="Could not load the desk" body="Check your connection and pull down to try again." />
        : <Empty title="Nothing here yet" body={filtered ? "Try another field or region." : "The desk has not published today's stories yet."} />
      }
      ListFooterComponent={data && items.length > limit ? <Button ghost label="Show more" onPress={() => setLimit((l) => l + PAGE)} style={{ marginTop: 14, alignItems: "center" }} /> : null}
      contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 24 }}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={t.muted} />}
      keyboardShouldPersistTaps="handled"
    />
  );
}
