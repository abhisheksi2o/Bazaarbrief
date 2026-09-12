import { FlatList } from "react-native";

import { StoryRow } from "@/components/story-row";
import { Empty, SectionHead } from "@/components/ui";
import { useDesk } from "@/lib/data";
import { usePrefs } from "@/lib/store";
import type { Article } from "@/lib/types";

export default function SavedScreen() {
  const { byId } = useDesk();
  const { prefs } = usePrefs();
  const items = prefs.saved.map(byId).filter((a): a is Article => !!a);
  return (
    <FlatList<Article>
      data={items}
      keyExtractor={(a) => a.id}
      renderItem={({ item }) => <StoryRow article={item} />}
      ListHeaderComponent={<SectionHead title="Saved for later" sub={items.length ? `${items.length} saved` : undefined} />}
      ListEmptyComponent={<Empty title="Nothing saved" body={prefs.saved.length ? "Saved stories drop off once they leave the desk's 24-hour window." : "Open a story and tap Save to keep it here."} />}
      contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 24 }}
    />
  );
}
