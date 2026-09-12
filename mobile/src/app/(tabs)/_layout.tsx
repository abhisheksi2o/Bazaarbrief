import Ionicons from "@expo/vector-icons/Ionicons";
import { Tabs } from "expo-router";
import { Text, type ColorValue } from "react-native";

import { Masthead } from "@/components/masthead";
import { usePrefs } from "@/lib/store";
import { fonts, useTokens } from "@/lib/theme";

type IconName = React.ComponentProps<typeof Ionicons>["name"];

function icon(name: IconName) {
  return ({ color, size }: { color: ColorValue; size: number }) => <Ionicons name={name} color={color} size={size} />;
}

export default function TabLayout() {
  const t = useTokens();
  const { prefs } = usePrefs();
  return (
    <Tabs
      screenOptions={{
        header: () => <Masthead />,
        tabBarActiveTintColor: t.accent,
        tabBarInactiveTintColor: t.muted,
        tabBarStyle: { backgroundColor: t.surface, borderTopColor: t.line },
        tabBarLabelStyle: { fontFamily: fonts.sansMedium, fontSize: 11 },
        sceneStyle: { backgroundColor: t.surface },
      }}>
      <Tabs.Screen name="index" options={{ title: "Today", tabBarIcon: icon("newspaper-outline") }} />
      <Tabs.Screen name="fields" options={{ title: "Fields", tabBarIcon: icon("grid-outline") }} />
      <Tabs.Screen name="recap" options={{ title: "Recap", tabBarIcon: icon("document-text-outline") }} />
      <Tabs.Screen name="markets" options={{ title: "Markets", tabBarIcon: icon("trending-up-outline") }} />
      <Tabs.Screen
        name="saved"
        options={{
          title: "Saved",
          tabBarIcon: icon("bookmark-outline"),
          tabBarBadge: prefs.saved.length || undefined,
          tabBarBadgeStyle: { backgroundColor: t.accent, color: t.accentInk, fontFamily: fonts.mono, fontSize: 10 },
        }}
      />
    </Tabs>
  );
}

export function TabHint({ children }: { children: string }) {
  const t = useTokens();
  return <Text style={{ fontFamily: fonts.sans, fontSize: 12, color: t.muted }}>{children}</Text>;
}
