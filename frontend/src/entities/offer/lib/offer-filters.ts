// Bosh sahifadagi batafsil filtrlar. Qirralar (`row.facets`) backend'da
// hisoblanadi (app/offer_facets.py): kredit turi, muddat (oy), valyuta,
// karta turi va to'lov tizimi.

export type TermBucket = { key: string; from: number; to: number | null };

// Omonat qisqa, kredit uzoq muddatli — oraliqlar shunga mos.
export const TERM_BUCKETS: Record<string, TermBucket[]> = {
  deposit: [
    { key: "0-6", from: 0, to: 6 },
    { key: "7-12", from: 7, to: 12 },
    { key: "13-24", from: 13, to: 24 },
    { key: "25+", from: 25, to: null },
  ],
  credit: [
    { key: "0-12", from: 0, to: 12 },
    { key: "13-36", from: 13, to: 36 },
    { key: "37-84", from: 37, to: 84 },
    { key: "85+", from: 85, to: null },
  ],
};

function inBucket(months: number | null | undefined, bucket: TermBucket | undefined): boolean {
  if (!bucket || months == null) return false;
  return months >= bucket.from && (bucket.to == null || months <= bucket.to);
}

export function matchesOfferFilters(row: any, product: string, filters: Record<string, string>): boolean {
  const facets = row.facets ?? {};
  for (const [key, value] of Object.entries(filters)) {
    if (key === "term") {
      const bucket = TERM_BUCKETS[product]?.find(b => b.key === value);
      if (!inBucket(facets.term_months, bucket)) return false;
    } else if (key === "online" || key === "kids") {
      if (!facets[key]) return false;
    } else if (facets[key] !== value) {
      return false;
    }
  }
  return true;
}
