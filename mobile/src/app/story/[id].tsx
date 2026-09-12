import { useLocalSearchParams, useRouter } from "expo-router";
import * as WebBrowser from "expo-web-browser";
import { useEffect } from "react";
import { Pressable, ScrollView, Share, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Button, Empty, Eyebrow, SectionTag } from "@/components/ui";
import { useDesk } from "@/lib/data";
import { istTimeLabel } from "@/lib/format";
import { usePrefs } from "@/lib/store";
import { fonts, useTokens } from "@/lib/theme";

export default function StoryScreen() {
  const t = useTokens();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { id } = useLocalSearchParams<{ id: string }>();
  const { byId } = useDesk();
  const { markRead, toggleSaved, isSaved } = usePrefs();
  const a = id ? byId(id) : undefined;

  useEffect(() => {
    if (a) markRead(a.id);
  }, [a, markRead]);

  if (!a) {
    return (
      <View style={{ flex: 1, paddingTop: insets.top + 20, paddingHorizontal: 20, backgroundColor: t.surface }}>
        <Empty title="Story not on the desk" body="It may have dropped out of the 24-hour window. Go back and pull to refresh." />
        <Button ghost label="Back" onPress={() => router.back()} style={{ alignSelf: "center" }} />
      </View>
    );
  }
  const saved = isSaved(a.id);
  const also = (a.sources ?? []).filter((s) => s !== a.source);

  return (
    <ScrollView style={{ backgroundColor: t.surface }} contentContainerStyle={{ paddingHorizontal: 20, paddingTop: insets.top + 12, paddingBottom: insets.bottom + 28 }}>
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <View style={{ width: 40, height: 4, borderRadius: 2, backgroundColor: t.line, alignSelf: "center" }} />
        <Pressable onPress={() => router.back()} hitSlop={12} accessibilityLabel="Close">
          <Text style={{ fontFamily: fonts.sansSemi, fontSize: 14, color: t.accent }}>Close</Text>
        </Pressable>
      </View>
      <View style={{ flexDirection: "row", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
        <SectionTag id={a.section} />
        <Text style={{ fontFamily: fonts.sansBold, fontSize: 10.5, letterSpacing: 1, color: t.faint }}>{a.region === "india" ? "INDIA" : "WORLD"}</Text>
        <Text style={{ fontFamily: fonts.sans, fontSize: 12.5, color: t.muted }}>{a.source} · {istTimeLabel(a.publishedAt)}</Text>
      </View>
      <Text style={{ fontFamily: fonts.serifBold, fontSize: 25, lineHeight: 30, color: t.ink, marginTop: 10, marginBottom: 10 }}>{a.title}</Text>
      <Text style={{ fontFamily: fonts.sans, fontSize: 16, lineHeight: 25, color: a.summary ? t.ink2 : t.muted }}>
        {a.summary || "No summary available for this story. Open the source for the full report."}
      </Text>
      {!!a.why && (
        <View style={{ marginTop: 14, backgroundColor: t.accentSoft, borderRadius: 10, paddingHorizontal: 14, paddingVertical: 12 }}>
          <Eyebrow style={{ color: t.accent, marginBottom: 4 }}>Why it matters</Eyebrow>
          <Text style={{ fontFamily: fonts.sans, fontSize: 15, lineHeight: 22, color: t.ink }}>{a.why}</Text>
        </View>
      )}
      {also.length > 0 && <Text style={{ marginTop: 12, fontFamily: fonts.sans, fontSize: 12.5, color: t.muted }}>Also covered by {also.join(", ")}</Text>}
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 18 }}>
        <Button label={`Read at ${a.source} ↗`} onPress={() => WebBrowser.openBrowserAsync(a.url)} />
        <Button ghost label={saved ? "Unsave" : "Save"} onPress={() => toggleSaved(a.id)} />
        <Button ghost label="Share" onPress={() => Share.share({ message: `${a.title}\n${a.url}`, url: a.url, title: a.title })} />
      </View>
    </ScrollView>
  );
}
