export type Region = "india" | "world";

export interface Article {
  id: string;
  title: string;
  summary?: string;
  source: string;
  url: string;
  publishedAt: string;
  section: string;
  region: Region;
  score?: number;
  sources?: string[];
  why?: string;
}

export interface Feed {
  updatedAt: string;
  articles: Article[];
  count: number;
  sessionLabel?: string;
  sources?: string[];
}

export interface Quote {
  symbol: string;
  label: string;
  group: string;
  kind: "index" | "fx" | "yield" | "usd" | "vol" | string;
  price: number;
  prevClose: number;
  change: number;
  changePct: number;
  weekPct: number;
  monthPct: number;
  high52?: number | null;
  low52?: number | null;
  currency?: string | null;
  asOf: string;
  spark: number[];
  sparkDates?: string[];
  error?: string;
}

export interface Markets {
  updatedAt: string;
  quotes: Quote[];
}

export interface ScoreEntry {
  label: string;
  value: string;
  changePct?: number | null;
  change?: string;
}

export interface RecapItem {
  text: string;
  ids?: string[];
}

export interface RecapGroup {
  label: string;
  items: RecapItem[];
}

export interface Daily {
  date: string;
  dateLabel?: string;
  sessionLabel?: string;
  readMinutes?: number;
  updatedAt?: string;
  title: string;
  standfirst?: string;
  scoreboard?: ScoreEntry[];
  groups?: RecapGroup[];
  watch?: string[];
}

export interface Weekly {
  week: string;
  rangeLabel?: string;
  readMinutes?: number;
  updatedAt?: string;
  title: string;
  standfirst?: string;
  scoreboard?: ScoreEntry[];
  groups?: RecapGroup[];
  watch?: string[];
}

export interface Archive {
  updatedAt?: string;
  dailies: Daily[];
  weeklies: Weekly[];
}

export interface PaperEdition {
  date: string;
  file: string;
  number: number;
  pages: number;
  title?: string;
  bytes?: number;
  builtAt?: string;
}

export interface PaperIndex {
  latest?: PaperEdition;
  editions: PaperEdition[];
  updatedAt?: string;
}

export interface DeskData {
  feed: Feed;
  markets: Markets;
  archive: Archive;
  paper?: PaperIndex | null;
  fetchedAt: number;
}
