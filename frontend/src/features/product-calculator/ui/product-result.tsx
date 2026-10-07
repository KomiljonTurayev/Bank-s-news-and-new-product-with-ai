import { useEffect, useRef, useState } from "react";
import { notifications } from "@mantine/notifications";

import { useI18n } from "@/shared/lib/i18n/i18n-context";
import { useOpenScreen } from "@/shared/lib/nav/use-open-screen";
import { useCurrency } from "@/entities/currency";
import { fetchJSON, apiFetch, invalidateJsonCache } from "@/shared/api/base";
import { fmtRate } from "@/shared/lib/format";

import { productTypeLabel, categoryLabel, scoreRankText } from "../lib/product-labels";
import MarketBars from "./market-bars";
import CurrencyWidget from "./currency-widget";

function scoreColorOf(score: number): string {
  if (score >= 70) return "#16a34a";
  if (score >= 40) return "#eab308";
  return "var(--accent)";
}

function deleteFailMessage(status: number, t: (key: string, vars?: any) => string): string {
  if (status === 422) return t("delete_error_invalid_msg");
  if (status === 429) return t("delete_error_rate_msg");
  return t("delete_error_server_msg", { status });
}

const CONFIRM_MS = 4000;

function StatPills({
  product,
  t,
  locale,
}: Readonly<{
  product: any;
  t: (key: string, vars?: any) => string;
  locale?: string;
}>) {
  const pills: [string, string][] = [
    [t("field_rate_label").replace(" *", "").replace(" (%)", ""), `${product.rate}%`],
  ];
  if (product.term_months)
    pills.push([t("field_term_label"), `${product.term_months} ${t("months_suffix")}`]);
  if (product.initial_payment_pct)
    pills.push([
      t("field_initial_payment_label").replace(" (%)", ""),
      `${product.initial_payment_pct}%`,
    ]);
  if (product.max_amount)
    pills.push([
      t("field_max_amount_label"),
      `${fmtRate(product.max_amount, locale)} ${product.currency}`,
    ]);

  return (
    <div className="pp-stat-pills">
      {pills.map(([label, value]) => (
        <div className="pp-stat-pill" key={label}>
          <span className="pp-stat-label">{label}</span>
          <span className="pp-stat-value">{value}</span>
        </div>
      ))}
    </div>
  );
}

export default function ProductResult({ id }: Readonly<{ id: number }>) {
  const { t, lang, locale } = useI18n();
  const { getCachedStats, fetchStats } = useCurrency();
  const { open, openChild } = useOpenScreen();
  const [product, setProduct] = useState<any>(null);
  // "product" ikkinchi bir tahlilga o'tilganda (masalan ro'yxatga qaytmasdan
  // to'g'ridan-to'g'ri boshqa id'ga) yangi so'rov tugaguncha ESKI mahsulotni
  // saqlab turadi — productId joriy id bilan mos kelmasa, uni "hali tayyor
  // emas" deb hisoblaymiz, aks holda bir render freymi davomida boshqa
  // mahsulotning nomi/tahlili ko'rinib qolardi.
  const [productId, setProductId] = useState<number | null>(null);
  const [error, setError] = useState(false);
  const [currencyEntry, setCurrencyEntry] = useState<any>(null);
  const [deleting, setDeleting] = useState(false);
  const [confirmDel, setConfirmDel] = useState(false);
  const confirmTimer = useRef<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    setError(false);
    setProduct(null);
    setProductId(null);
    setCurrencyEntry(null);
    fetchJSON(`/api/products/${id}?lang=${lang}`)
      .then(async p => {
        if (cancelled) return;
        setProduct(p);
        setProductId(id);
        if (p.currency && p.currency !== "UZS") {
          try {
            const stats = getCachedStats("30") ?? (await fetchStats("30"));
            const entry = stats.find((s: any) => s.code === p.currency);
            if (!cancelled && entry) setCurrencyEntry(entry);
          } catch {
            // Valyuta ma'lumotini yuklab bo'lmasa ham, asosiy tahlil ko'rinishda davom etadi.
          }
        }
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });
    return () => {
      cancelled = true;
    };
  }, [id, lang]);

  useEffect(
    () => () => {
      if (confirmTimer.current !== null) window.clearTimeout(confirmTimer.current);
    },
    [],
  );

  const disarmDelete = () => {
    if (confirmTimer.current !== null) window.clearTimeout(confirmTimer.current);
    confirmTimer.current = null;
    setConfirmDel(false);
  };

  async function handleDelete() {
    if (deleting) return;
    setDeleting(true);
    try {
      const response = await apiFetch(`/api/products/${id}`, { method: "DELETE" });
      // Natijasi nima bo'lmasin, ro'yxat bo'yicha keshlangan javob endi
      // ishonchsiz — keyishi ochilganda u API'dan qayta olinadi.
      invalidateJsonCache("/api/products");
      if (response.ok) {
        notifications.show({
          title: t("delete_success_title"),
          message: t("delete_success_msg"),
          color: "green",
          autoClose: 4000,
        });
        open("/products");
      } else if (response.status === 404) {
        // Mahsulot allaqachon o'chirilgan — xato emas, shunchaki ro'yxatga
        // qaytamiz (u yerda o'zi yo'qolganini ko'radi).
        open("/products");
      } else {
        notifications.show({
          title: t("delete_error_title"),
          message: deleteFailMessage(response.status, t),
          color: "red",
          autoClose: 5000,
        });
      }
    } catch {
      notifications.show({
        title: t("delete_error_title"),
        message: t("delete_error_offline_msg"),
        color: "red",
        autoClose: 5000,
      });
    } finally {
      setDeleting(false);
    }
  }

  if (error) {
    return <p className="form-error">{t("analysis_load_error")}</p>;
  }
  if (!product || productId !== id) {
    return <p className="empty-note">{t("bank_grid_loading")}</p>;
  }

  const a = product.analysis;
  const badge = product.category
    ? categoryLabel(product.category, t)
    : productTypeLabel(product.product_type, t);
  const scoreColor = scoreColorOf(a.score);

  return (
    <div className="product-result">
      <div className="pp-result-card">
        <div className="pp-result-hero-top">
          <div>
            <div className="pp-result-badges">
              <span className="pp-pill">{badge}</span>
              {product.bank_name && <span className="pp-result-bank">· {product.bank_name}</span>}
            </div>
            <h1 className="pp-result-title">{product.name}</h1>
            {product.purpose && <p className="pp-result-purpose">{product.purpose}</p>}
          </div>
          <div className="pp-result-actions">
            <button
              type="button"
              className="btn-secondary"
              onClick={() => openChild(`/products/${id}/edit`)}>
              <svg
                viewBox="0 0 24 24"
                width="14"
                height="14"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true">
                <path d="M4 20h4L20 8l-4-4L4 16v4Z" />
                <path d="M13.5 6.5 17.5 10.5" />
              </svg>
              {t("edit_btn")}
            </button>
            <button
              type="button"
              className={`btn-delete${confirmDel ? " arm-del" : ""}`}
              title={t("delete_btn")}
              disabled={deleting}
              aria-pressed={confirmDel}
              onBlur={() => {
                if (confirmDel) disarmDelete();
              }}
              onClick={() => {
                if (deleting) return;
                if (confirmDel) {
                  disarmDelete();
                  handleDelete();
                } else {
                  setConfirmDel(true);
                  if (confirmTimer.current !== null) window.clearTimeout(confirmTimer.current);
                  confirmTimer.current = window.setTimeout(disarmDelete, CONFIRM_MS);
                }
              }}>
              <svg
                viewBox="0 0 24 24"
                width="14"
                height="14"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true">
                <path d="M4 7h16M9.5 7V4.8h5V7M6.5 7l.9 13.2h9.2L17.5 7M10 10.8v5.8M14 10.8v5.8" />
              </svg>
              {confirmDel ? t("delete_confirm_btn") : t("delete_btn")}
            </button>
          </div>
        </div>
        <StatPills product={product} t={t} locale={locale} />
      </div>
      <div className="pp-result-body">
        <div className="pp-result-grid">
          <div className="pp-card">
            <div className="pp-card-label">{t("pp_overall_assessment")}</div>
            <p className="pp-result-summary">{a.summary}</p>
            {a.strengths.map((s: string) => (
              <div className="pp-result-callout" key={`s:${s}`}>
                {s}
              </div>
            ))}
            {a.cautions.map((s: string) => (
              <div className="pp-result-callout caution" key={`c:${s}`}>
                {s}
              </div>
            ))}
          </div>
          {a.score !== null && (
            <div className="pp-card pp-score-card">
              <div className="pp-card-label">{t("score_label")}</div>
              <div
                className="pp-score-gauge"
                style={{ "--score": a.score, "--score-color": scoreColor } as React.CSSProperties}>
                <span>{a.score}</span>
              </div>
              <p className="pp-score-sub">{t("score_sub")}</p>
              <p className="pp-score-rank" style={{ color: scoreColor }}>
                {scoreRankText(a.score, t)}
              </p>
            </div>
          )}
        </div>
        <MarketBars product={product} analysis={a} />
        {currencyEntry && <CurrencyWidget code={product.currency} entry={currencyEntry} />}
      </div>
    </div>
  );
}
