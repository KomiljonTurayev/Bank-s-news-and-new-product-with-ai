import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { useI18n } from "@/shared/lib/i18n/i18n-context";
import { fetchJSON } from "@/shared/api/base";

import { productTypeLabel } from "../lib/product-labels";

// ═══════════════════════════════════════════════════════════════════
// BOZORNI BATAFSIL SOLISHTIRISH — `GET /api/products/market-compare`.
// Muddat (oy) va summa backend'da raqamga keltirilgan; bu yerda muddat
// oraliqlari bo'yicha statistika kartalari va saralanadigan jadval.
// AI ishlatilmaydi — bepul va bir zumda.
// ═══════════════════════════════════════════════════════════════════

type ProductType = "credit" | "deposit" | "card" | "investment";
const PRODUCT_TYPES: ProductType[] = ["deposit", "credit", "card", "investment"];
const PAGE_SIZE = 25;

type Offer = {
  bank_code: string;
  bank_name: string;
  name: string;
  category: string | null;
  rate: number;
  term_months: number | null;
  term_text: string | null;
  min_amount: number | null;
  max_amount: number | null;
  amount_text: string | null;
  url: string | null;
};

type Stats = {
  count: number;
  min_rate: number;
  avg_rate: number;
  max_rate: number;
  banks: number;
  best: Offer;
};

type Bucket = Stats & { key: string; from_months: number; to_months: number | null };
type CategoryStats = Stats & { name: string };

type CompareData = {
  lower_is_better: boolean;
  overall: Stats | null;
  term_buckets: Bucket[];
  categories: CategoryStats[];
  offers: Offer[];
};

type SortKey = "rate" | "term_months" | "min_amount" | "max_amount";

function formatMoney(value: number | null, t: (key: string) => string): string {
  if (value == null) return "—";
  const fmt = (n: number) => (Number.isInteger(n) ? String(n) : n.toFixed(1));
  if (value >= 1e9) return `${fmt(value / 1e9)} ${t("mc_bln")}`;
  if (value >= 1e6) return `${fmt(value / 1e6)} ${t("mc_mln")}`;
  if (value >= 1e3) return `${fmt(value / 1e3)} ${t("mc_k")}`;
  return String(value);
}

function bucketLabel(b: Bucket, t: (key: string, vars?: Record<string, any>) => string): string {
  return b.to_months == null
    ? t("mc_bucket_from", { from: b.from_months })
    : t("mc_bucket_range", { from: b.from_months, to: b.to_months });
}

export default function MarketCompare() {
  const { t } = useI18n();
  const [productType, setProductType] = useState<ProductType>("deposit");
  const [category, setCategory] = useState<string>("");
  const [bucket, setBucket] = useState<string | null>(null);
  const [sort, setSort] = useState<{ key: SortKey; desc: boolean } | null>(null);
  const [shown, setShown] = useState(PAGE_SIZE);

  const query = category ? `&category=${encodeURIComponent(category)}` : "";
  const { data, isLoading } = useQuery<CompareData>({
    queryKey: ["market-compare", productType, category],
    queryFn: () => fetchJSON(`/api/products/market-compare?product_type=${productType}${query}`),
    staleTime: 5 * 60_000,
  });

  function selectType(type: ProductType) {
    setProductType(type);
    setCategory("");
    setBucket(null);
    setSort(null);
    setShown(PAGE_SIZE);
  }

  function toggleSort(key: SortKey) {
    setSort(s => (s?.key === key ? { key, desc: !s.desc } : { key, desc: key !== "rate" || !data?.lower_is_better }));
  }

  const rows = useMemo(() => {
    if (!data) return [];
    const active = data.term_buckets.find(b => b.key === bucket);
    let list = active
      ? data.offers.filter(
          o =>
            o.term_months != null &&
            o.term_months >= active.from_months &&
            (active.to_months == null || o.term_months <= active.to_months),
        )
      : data.offers;
    if (sort) {
      const dir = sort.desc ? -1 : 1;
      list = [...list].sort((a, b) => {
        const av = a[sort.key];
        const bv = b[sort.key];
        if (av == null) return 1;
        if (bv == null) return -1;
        return (av - bv) * dir;
      });
    }
    return list;
  }, [data, bucket, sort]);

  const sortMark = (key: SortKey) => (sort?.key === key ? (sort.desc ? " ↓" : " ↑") : "");
  const overall = data?.overall;

  return (
    <section className="mc" aria-label={t("mc_title")}>
      <header className="mc-head">
        <div>
          <h3>{t("mc_title")}</h3>
          <p>{t(data?.lower_is_better ? "mc_subtitle_low" : "mc_subtitle_high")}</p>
        </div>
        <div className="mc-types" role="radiogroup" aria-label={t("ai_type_label")}>
          {PRODUCT_TYPES.map(type => (
            <button
              key={type}
              type="button"
              role="radio"
              aria-checked={productType === type}
              className={`ai-type${productType === type ? " active" : ""}`}
              onClick={() => selectType(type)}>
              {productTypeLabel(type, t)}
            </button>
          ))}
        </div>
      </header>

      {isLoading && <p className="mc-empty">{t("mc_loading")}</p>}
      {!isLoading && !overall && <p className="mc-empty">{t("mc_empty")}</p>}

      {overall && data && (
        <>
          <dl className="mc-overall">
            <div>
              <dt>{t("mc_offers")}</dt>
              <dd>{overall.count}</dd>
            </div>
            <div>
              <dt>{t("mc_banks")}</dt>
              <dd>{overall.banks}</dd>
            </div>
            <div>
              <dt>{t("mc_min")}</dt>
              <dd>{overall.min_rate}%</dd>
            </div>
            <div>
              <dt>{t("mc_avg")}</dt>
              <dd>{overall.avg_rate}%</dd>
            </div>
            <div>
              <dt>{t("mc_max")}</dt>
              <dd>{overall.max_rate}%</dd>
            </div>
          </dl>

          {data.categories.length > 1 && (
            <label className="mc-category">
              <span>{t("mc_category")}</span>
              <select
                value={category}
                onChange={e => {
                  setCategory(e.target.value);
                  setBucket(null);
                  setShown(PAGE_SIZE);
                }}>
                <option value="">{t("mc_all")}</option>
                {data.categories.map(c => (
                  <option key={c.name} value={c.name}>
                    {c.name} ({c.count}) · {c.avg_rate}%
                  </option>
                ))}
              </select>
            </label>
          )}

          <h4 className="ai-leaders-title">{t("mc_by_term")}</h4>
          <div className="mc-buckets">
            {data.term_buckets.map(b => {
              // Shkala: umumiy min..max ichida shu oraliqning min..max'i.
              const span = overall.max_rate - overall.min_rate || 1;
              const left = ((b.min_rate - overall.min_rate) / span) * 100;
              const width = Math.max(((b.max_rate - b.min_rate) / span) * 100, 2);
              const avg = ((b.avg_rate - overall.min_rate) / span) * 100;
              return (
                <button
                  key={b.key}
                  type="button"
                  className={`mc-bucket${bucket === b.key ? " active" : ""}`}
                  aria-pressed={bucket === b.key}
                  onClick={() => {
                    setBucket(cur => (cur === b.key ? null : b.key));
                    setShown(PAGE_SIZE);
                  }}>
                  <span className="mc-bucket-term">{bucketLabel(b, t)}</span>
                  <span className="mc-bucket-count">
                    {t("mc_bucket_count", { count: b.count, banks: b.banks })}
                  </span>
                  <span className="mc-range" aria-hidden="true">
                    <span className="mc-range-bar" style={{ left: `${left}%`, width: `${width}%` }} />
                    <span className="mc-range-avg" style={{ left: `${avg}%` }} />
                  </span>
                  <span className="mc-bucket-rates">
                    <span>{b.min_rate}%</span>
                    <b>
                      {t("mc_avg")} {b.avg_rate}%
                    </b>
                    <span>{b.max_rate}%</span>
                  </span>
                  <span className="mc-bucket-best">
                    {t("mc_best")}: <b>{b.best.bank_name}</b> · {b.best.name} · <b>{b.best.rate}%</b>
                  </span>
                </button>
              );
            })}
          </div>

          <div className="compare-table-wrap mc-table-wrap">
            <table className="compare-table mc-table">
              <thead>
                <tr>
                  <th>{t("compare_col_bank")}</th>
                  <th>{t("compare_col_product")}</th>
                  <th>
                    <button type="button" onClick={() => toggleSort("rate")}>
                      {t("compare_col_rate")}
                      {sortMark("rate")}
                    </button>
                  </th>
                  <th>
                    <button type="button" onClick={() => toggleSort("term_months")}>
                      {t("mc_col_term")}
                      {sortMark("term_months")}
                    </button>
                  </th>
                  <th>
                    <button type="button" onClick={() => toggleSort("min_amount")}>
                      {t("mc_col_min")}
                      {sortMark("min_amount")}
                    </button>
                  </th>
                  <th>
                    <button type="button" onClick={() => toggleSort("max_amount")}>
                      {t("mc_col_max")}
                      {sortMark("max_amount")}
                    </button>
                  </th>
                </tr>
              </thead>
              <tbody>
                {rows.slice(0, shown).map(o => (
                  <tr key={`${o.bank_code}-${o.name}-${o.category ?? ""}`}>
                    <td>{o.bank_name}</td>
                    <td>
                      {o.url ? (
                        <a href={o.url} target="_blank" rel="noopener noreferrer">
                          {o.name || "—"}
                        </a>
                      ) : (
                        o.name || "—"
                      )}
                      {o.category && <span className="mc-cat"> · {o.category}</span>}
                    </td>
                    <td className="mc-rate">{o.rate}%</td>
                    <td title={o.term_text ?? undefined}>
                      {o.term_months != null ? t("mc_months", { n: o.term_months }) : (o.term_text ?? "—")}
                    </td>
                    <td title={o.amount_text ?? undefined}>{formatMoney(o.min_amount, t)}</td>
                    <td title={o.amount_text ?? undefined}>{formatMoney(o.max_amount, t)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {rows.length > shown && (
            <button type="button" className="mc-more" onClick={() => setShown(n => n + PAGE_SIZE)}>
              {t("mc_more", { n: rows.length - shown })}
            </button>
          )}
          <p className="mc-note">{t("mc_note")}</p>
        </>
      )}
    </section>
  );
}
