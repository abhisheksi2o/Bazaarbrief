import Svg, { Circle, Path } from "react-native-svg";

import { useTokens } from "@/lib/theme";

export function Sparkline({ values, width = 72, height = 28 }: { values: number[]; width?: number; height?: number }) {
  const t = useTokens();
  if (!values || values.length < 2) return null;
  const p = 2;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const rng = max - min || 1;
  const pts = values.map((v, i) => [p + (i * (width - 2 * p)) / (values.length - 1), height - p - ((v - min) / rng) * (height - 2 * p)] as const);
  const d = pts.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`).join(" ");
  const up = values[values.length - 1] >= values[0];
  const col = up ? t.gain : t.loss;
  const last = pts[pts.length - 1];
  const area = `${d} L${last[0].toFixed(1)} ${height} L${pts[0][0].toFixed(1)} ${height} Z`;
  return (
    <Svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      <Path d={area} fill={col} opacity={0.12} />
      <Path d={d} fill="none" stroke={col} strokeWidth={1.5} strokeLinejoin="round" />
      <Circle cx={last[0]} cy={last[1]} r={2} fill={col} />
    </Svg>
  );
}
