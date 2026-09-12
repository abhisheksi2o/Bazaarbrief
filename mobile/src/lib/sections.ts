export interface Section {
  id: string;
  label: string;
  short: string;
  hue: number;
  blurb: string;
}

export const SECTIONS: Section[] = [
  { id: "stocks", label: "Stocks", short: "Stocks", hue: 212, blurb: "Sensex, Nifty, IPOs, FII flows" },
  { id: "global-markets", label: "Global Markets", short: "Global", hue: 262, blurb: "Wall Street, Asia, Europe" },
  { id: "economy", label: "Economy & GDP", short: "Economy", hue: 158, blurb: "Growth, jobs, trade, fiscal" },
  { id: "inflation", label: "Inflation & Prices", short: "Inflation", hue: 18, blurb: "CPI, WPI, food and fuel" },
  { id: "central-banks", label: "RBI & Central Banks", short: "Central banks", hue: 286, blurb: "Rates, liquidity, Fed, ECB" },
  { id: "bonds", label: "Bonds & Rates", short: "Bonds", hue: 190, blurb: "G-secs, yields, treasuries" },
  { id: "fx-commodities", label: "Currency & Commodities", short: "Rupee & commodities", hue: 38, blurb: "Rupee, dollar, crude, gold" },
  { id: "corporate", label: "Corporate & Earnings", short: "Corporate", hue: 230, blurb: "Results, deals, boardrooms" },
  { id: "policy", label: "Policy & Government", short: "Policy", hue: 330, blurb: "Budget, taxes, SEBI, regulation" },
  { id: "geopolitics", label: "Geopolitics & Trade", short: "Geopolitics", hue: 0, blurb: "Tariffs, sanctions, conflict" },
  { id: "banking", label: "Banking & Finance", short: "Banking", hue: 120, blurb: "Banks, NBFCs, credit, fintech" },
  { id: "crypto", label: "Crypto", short: "Crypto", hue: 48, blurb: "Bitcoin, stablecoins, regulation" },
];

export const SECTION_BY_ID: Record<string, Section> = Object.fromEntries(SECTIONS.map((s) => [s.id, s]));

export function sectionOf(id: string): Section {
  return SECTION_BY_ID[id] ?? { id, label: id, short: id, hue: 200, blurb: "" };
}
