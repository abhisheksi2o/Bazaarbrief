import { useState } from "react";
import { ScrollView, View } from "react-native";

import { DateStrip, RecapView } from "@/components/recap-view";
import { Empty, Segmented } from "@/components/ui";
import { useDesk } from "@/lib/data";

export default function RecapScreen() {
  const { data, loading } = useDesk();
  const [span, setSpan] = useState<"day" | "week">("day");
  const [day, setDay] = useState<string | null>(null);
  const dailies = data?.archive.dailies ?? [];
  const weeklies = data?.archive.weeklies ?? [];
  const active = dailies.find((d) => d.date === day) ?? dailies[0];

  return (
    <ScrollView contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 28 }}>
      <View style={{ marginTop: 14, flexDirection: "row" }}>
        <Segmented value={span} onChange={setSpan} options={[{ value: "day", label: "Recap of the day" }, { value: "week", label: "Recap of the week" }]} />
      </View>
      {span === "day" ? (
        active ? (
          <View>
            <DateStrip items={dailies.slice(0, 8).map((d) => ({ key: d.date, label: d.dateLabel ?? d.date }))} active={active.date} onSelect={setDay} />
            <RecapView doc={active} kind="day" />
          </View>
        ) : (
          <Empty title={loading ? "Loading…" : "No recap yet"} body="The desk writes the recap of the day at the close and again in the evening." />
        )
      ) : weeklies[0] ? (
        <RecapView doc={weeklies[0]} kind="week" />
      ) : (
        <Empty title="No weekly recap yet" body="The recap of the week is written every Friday evening after markets close." />
      )}
    </ScrollView>
  );
}
