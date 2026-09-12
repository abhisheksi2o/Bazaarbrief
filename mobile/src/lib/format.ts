export const IST_OFFSET_MIN = 330;

export function ago(iso: string, now: number = Date.now()): string {
  const t = Date.parse(iso);
  if (!t) return "";
  const m = Math.round((now - t) / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.round(h / 24);
  return d === 1 ? "yesterday" : `${d}d ago`;
}

export function num(v: number | null | undefined, dp?: number): string {
  if (v == null || Number.isNaN(v)) return "–";
  const abs = Math.abs(v);
  const d = dp ?? (abs >= 1000 ? 0 : abs >= 100 ? 1 : 2);
  return v.toLocaleString("en-IN", { minimumFractionDigits: d, maximumFractionDigits: d });
}

export function pct(v: number | null | undefined): string {
  if (v == null || Number.isNaN(v)) return "–";
  return `${v > 0 ? "+" : ""}${v.toFixed(2)}%`;
}

export function sign(v: number | null | undefined): "up" | "down" | "flat" {
  if (v == null) return "flat";
  return v > 0.0001 ? "up" : v < -0.0001 ? "down" : "flat";
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

/** Date parts in Indian Standard Time without relying on Intl time-zone data on every device. */
export function istParts(date: Date = new Date()) {
  const shifted = new Date(date.getTime() + (IST_OFFSET_MIN + date.getTimezoneOffset()) * 60000);
  return {
    day: DAYS[shifted.getDay()],
    date: shifted.getDate(),
    month: MONTHS[shifted.getMonth()],
    hour: shifted.getHours(),
    minute: shifted.getMinutes(),
  };
}

export function istDateLabel(date: Date = new Date()): string {
  const p = istParts(date);
  return `${p.day}, ${p.date} ${p.month}`;
}

export function istTimeLabel(iso: string): string {
  const p = istParts(new Date(iso));
  const h12 = p.hour % 12 || 12;
  const ampm = p.hour < 12 ? "am" : "pm";
  return `${p.date} ${p.month}, ${h12}:${String(p.minute).padStart(2, "0")} ${ampm} IST`;
}

export function yieldChange(bp: number): string {
  const v = Math.round(bp * 100);
  return `${v > 0 ? "+" : ""}${v} bp`;
}
