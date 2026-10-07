import { useEffect, useState } from "react";

import { useI18n } from "@/shared/lib/i18n/i18n-context";
import { useCurrency } from "@/entities/currency";
import { fmtRate, changeDirection } from "@/shared/lib/format";
import Sparkline from "@/shared/ui/sparkline";

import MplBigChart from "./mpl-big-chart";

const PERIODS = [
  { value: "7", key: "period_7" },
  { value: "30", key: "period_30" },
  { value: "90", key: "period_90" },
  { value: "365", key: "period_365" },
  { value: "0", key: "period_0" },
];

// Hozirgi kurs davr oralig'ida qayerda turishini foizga aylantiradi —
// jadvaldagi oralıq chizig'idagi nuqta shu foizga qo'yiladi.
function positionPct(value: number, min: number, max: number) {
  const span = max - min;
  if (!span) return 50;
  return Math.min(100, Math.max(0, ((value - min) / span) * 100));
}

export default function MplScreen({
  openChartCode,
  setOpenChartCode,
}: Readonly<{
  openChartCode: string | null;
  setOpenChartCode: (code: string | null) => void;
}>) {
  const { t, locale, currencyName } = useI18n();
  const { getCachedStats, fetchStats, applyChanges } = useCurrency();
  const [period, setPeriod] = useState("30");
  const [stats, setStats] = useState<any[] | null>(() => getCachedStats("30") ?? null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setError(false);
    const cached = getCachedStats(period);
    if (cached) {
      setStats(cached);
      applyChanges(cached);
      return;
    }
    setStats(null);
    fetchStats(period)
      .then((s: any[]) => {
        if (cancelled) return;
        setStats(s);
        applyChanges(s);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });
    return () => {
      cancelled = true;
    };
  }, [period]);

  function handleRowClick(code: string) {
    setOpenChartCode(openChartCode === code ? null : code);
  }

  const periodLabel = t(`period_${period}`);
  const samples = stats?.length ? Math.max(...stats.map(s => s.samples || 0)) : 0;

  let tableRows: React.ReactNode = null;
  if (error) {
    tableRows = (
      <tr>
        <td colSpan={8} className="loading">
          {t("mpl_load_error")}
        </td>
      </tr>
    );
  } else if (stats === null) {
    tableRows = (
      <tr>
        <td colSpan={8} className="loading">
          {t("mpl_loading")}
        </td>
      </tr>
    );
  } else if (stats.length === 0) {
    tableRows = (
      <tr>
        <td colSpan={8} className="loading">
          {t("mpl_no_history")}
        </td>
      </tr>
    );
  } else {
    tableRows = stats.map(s => {
      const { dir, arrow } = changeDirection(s.change_pct);
      const active = s.code === openChartCode;
      const pct = positionPct(s.current, s.min, s.max);
      const avgPct = positionPct(s.avg, s.min, s.max);
      return (
        <tr
          key={s.code}
          className={active ? "active" : ""}
          title={t("mpl_row_open_title", { name: currencyName(s.code) })}
          onClick={() => handleRowClick(s.code)}>
          <td className="ccy-cell" data-label="">
            <button
              type="button"
              className="mpl-ccy-btn"
              aria-expanded={active}
              onClick={e => {
                // Qatorning o'zi bosiladi (onClick tr da), tugma — klaviatura/
                // ekran o'qigichlar uchun. Pufaklashmasligi kerak.
                e.stopPropagation();
                handleRowClick(s.code);
              }}>
              <span className="mpl-ccy-code">{s.code}</span>
              <span className="mpl-ccy-name">{currencyName(s.code)}</span>
              <span className="mpl-row-cta" aria-hidden="true">
                {active ? "▾" : "▸"}
              </span>
            </button>
          </td>
          <td className="num mpl-hist-col" data-label={t("mpl_col_min")}>
            {fmtRate(s.min, locale)}
          </td>
          <td className="num mpl-hist-col" data-label={t("mpl_col_avg")}>
            {fmtRate(s.avg, locale)}
          </td>
          <td className="num mpl-hist-col" data-label={t("mpl_col_max")}>
            {fmtRate(s.max, locale)}
          </td>
          <td
            className="mpl-range-col"
            data-label={t("mpl_col_range")}
            title={t("mpl_range_tip", {
              current: fmtRate(s.current, locale),
              min: fmtRate(s.min, locale),
              max: fmtRate(s.max, locale),
              pct: Math.round(pct),
            })}>
            <span className="mpl-range-wrap">
              <span className="mpl-range-track">
                <span className="mpl-range-avg" style={{ left: `${avgPct}%` }} />
                <span className={`mpl-range-dot mpl-${dir}`} style={{ left: `${pct}%` }} />
              </span>
              <span className="mpl-range-pct">{Math.round(pct)}%</span>
            </span>
          </td>
          <td className="num rate-cell mpl-now-col" data-label={t("mpl_col_current")}>
            {fmtRate(s.current, locale)}
          </td>
          <td className="num" data-label={t("mpl_col_change")}>
            <span className={`mpl-change mpl-${dir}`}>
              {arrow} {Math.abs(s.change_pct).toFixed(2)}%
            </span>
          </td>
          <td className="spark-td" data-label="">
            <Sparkline values={s.sparkline} />
          </td>
        </tr>
      );
    });
  }

  return (
    <div className="screen-overlay">
      <div className="screen-head">
        <h2>{t("mpl_screen_title")}</h2>
      </div>
      <div className="screen-body mpl-wide">
        <section className="mpl-section">
          <div className="mpl-head">
            <div className="mpl-head-info">
              <span className="mpl-head-title">{t("mpl_heading")}</span>
              <p className="mpl-meta">
                <span>{t("mpl_heading_source")}</span>
                <span>{periodLabel}</span>
                {samples > 0 && <span>{t("mpl_samples", { count: samples })}</span>}
                <span>{t("mpl_unit_som")}</span>
              </p>
            </div>
            <div className="mpl-controls">
              <span className="mpl-period-label">{t("mpl_period_label")}</span>
              {/* role="group" o'rnida oddiy div: .mpl-periods uslubi <fieldset> UA
                  margin/min-inline-size qiymatlarini qayta bermaydi — semantik role
                  vizual aushechilik keltirar edi. Yorliq matn yonda ko'rinib turadi,
                  tugmalarda aria-pressed bor. */}
              <div className="mpl-periods">
                {PERIODS.map(p => (
                  <button
                    key={p.value}
                    type="button"
                    className={p.value === period ? "active" : ""}
                    aria-pressed={p.value === period}
                    onClick={() => setPeriod(p.value)}>
                    {t(p.key)}
                  </button>
                ))}
              </div>
            </div>
          </div>
          <div className="mpl-table-wrap mpl-ccy-wrap">
            <table className="mpl-table mpl-ccy-table">
              <thead>
                <tr>
                  <th>{t("mpl_col_currency")}</th>
                  <th className="num mpl-hist-col">{t("mpl_col_min")}</th>
                  <th className="num mpl-hist-col">{t("mpl_col_avg")}</th>
                  <th className="num mpl-hist-col">{t("mpl_col_max")}</th>
                  <th className="mpl-range-col">{t("mpl_col_range")}</th>
                  <th className="num mpl-now-col">{t("mpl_col_current")}</th>
                  <th className="num">{t("mpl_col_change")}</th>
                  <th className="trend-col">{t("mpl_col_trend")}</th>
                </tr>
              </thead>
              <tbody>{tableRows}</tbody>
            </table>
          </div>
          <p className="mpl-hint">{t("mpl_hint", { period: periodLabel })}</p>
          {openChartCode && (
            <MplBigChart
              code={openChartCode}
              period={period}
              statsForPeriod={stats}
              onClose={() => setOpenChartCode(null)}
            />
          )}
        </section>
      </div>
    </div>
  );
}
