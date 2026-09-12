import { useRouter } from "expo-router";
import { memo } from "react";
import { Pressable, Text, View } from "react-native";

import { SectionTag } from "@/components/ui";
import { ago } from "@/lib/format";
import { usePrefs } from "@/lib/store";
import { fonts, useTokens } from "@/lib/theme";
import type { Article } from "@/lib/types";

export const StoryRow = memo(function StoryRow({ article, lead }: { article: Article; lead?: boolean }) {
  const t = useTokens();
  const router = useRouter();
  const { isRead, isSaved, prefs } = usePrefs();
  const read = isRead(article.id);
  const saved = isSaved(article.id);
  const isNew = !read && prefs.lastSeen > 0 && Date.parse(article.publishedAt) > prefs.lastSeen;
  return (
    <Pressable
      onPress={() => router.push({ pathname: "/story/[id]", params: { id: article.id } })}
      accessibilityRole="button"
      style={({ pressed }) => ({ paddingVertical: 14, borderBottomWidth: 1, borderBottomColor: t.line2, opacity: pressed ? 0.7 : 1 })}>
      <View style={{ flexDirection: "row", alignItems: "center", flexWrap: "wrap", gap: 8, marginBottom: 4 }}>
        <SectionTag id={article.section} />
        <Text style={{ fontFamily: fonts.sansBold, fontSize: 10.5, letterSpacing: 1, color: t.faint }}>{article.region === "india" ? "INDIA" : "WORLD"}</Text>
        <Text style={{ fontFamily: fonts.sans, fontSize: 12, color: t.muted }}>{article.source} · {ago(article.publishedAt)}</Text>
        {isNew && (
          <View style={{ backgroundColor: t.gainSoft, paddingHorizontal: 6, paddingVertical: 1, borderRadius: 999 }}>
            <Text style={{ fontFamily: fonts.sansBold, fontSize: 10, color: t.gain, letterSpacing: 0.6 }}>NEW</Text>
          </View>
        )}
      </View>
      <View style={{ flexDirection: "row", gap: 10, alignItems: "flex-start" }}>
        <Text style={{ flex: 1, fontFamily: lead ? fonts.serifBold : fonts.serif, fontSize: lead ? 24 : 19, lineHeight: lead ? 28 : 24, color: read ? t.muted : t.ink }}>
          {article.title}
        </Text>
        {saved && <Text style={{ color: t.accent, fontSize: 16, paddingTop: 4 }}>■</Text>}
      </View>
      {article.why ? (
        <View style={{ marginTop: 6, paddingLeft: 10, borderLeftWidth: 2, borderLeftColor: t.accent }}>
          <Text style={{ fontFamily: fonts.sans, fontSize: 13.5, lineHeight: 19, color: t.ink2 }}>{article.why}</Text>
        </View>
      ) : article.summary ? (
        <Text numberOfLines={lead ? 3 : 2} style={{ marginTop: 4, fontFamily: fonts.sans, fontSize: 13.5, lineHeight: 19, color: t.muted }}>
          {article.summary}
        </Text>
      ) : null}
    </Pressable>
  );
});
