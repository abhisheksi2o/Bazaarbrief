import { useLocalSearchParams, useRouter } from "expo-router";
import { FlatList, Pressable, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { StoryRow } from "@/components/story-row";
import { Empty, SectionHead } from "@/components/ui";
import { useDesk } from "@/lib/data";
import { sectionOf } from "@/lib/sections";
import { fonts, useTokens } from "@/lib/theme";
import type { Article } from "@/lib/types";

export default function FieldScreen() {
  const t = useTokens();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { id } = useLocalSearchParams<{ id: string }>();
  const { data } = useDesk();
  const s = sectionOf(id ?? "");
  const items = (data?.feed.articles ?? []).filter((a) => a.section === s.id);
  return (
    <FlatList<Article>
      data={items}
      keyExtractor={(a) => a.id}
      renderItem={({ item }) => <StoryRow article={item} />}
      ListHeaderComponent={
        <View style={{ paddingTop: insets.top + 8 }}>
          <Pressable onPress={() => router.back()} hitSlop={8}>
            <Text style={{ fontFamily: fonts.sansSemi, fontSize: 13.5, color: t.accent }}>← All fields</Text>
          </Pressable>
          <SectionHead title={s.label} sub={`${items.length} stories`} />
        </View>
      }
      ListEmptyComponent={<Empty title="Quiet field" body="No stories filed here in the last day." />}
      contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 24, backgroundColor: t.surface }}
      style={{ backgroundColor: t.surface }}
    />
  );
}
