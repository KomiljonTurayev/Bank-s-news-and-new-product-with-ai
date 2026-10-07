import { useEffect, useMemo, useRef, useState } from "react";

import { useI18n } from "@/shared/lib/i18n/i18n-context";
import { useCurrency } from "@/entities/currency";
import { fmtRate, fmtDate, fmtDateShort } from "@/shared/lib/format";
import { buildChartGeometry, statsFromPoints } from "@/shared/lib/mpl-chart";
import ChangeBadge from "@/shared/ui/change-badge";

function periodPhrase(period: string, t: (key: string, vars?: any) => string) {
  if (period === "0") return t("period_phrase_all");
  return t("period_phrase_recent", { period: t(`period_${period}`) });
}

// "Katta diagramma" — MPL jadvalidagi valyuta qatoriga bosilganda cbu.uz
// arxividan o'sha valyutaning to'liq tarixi (tanlangan davr bo'yicha)
// olinadi va gradient-fon, o'qlar va hover tooltip bilan chiziladi.
export default function MplBigChart({
  code,
  period,
  statsForPeriod,
  onClose,
}: Readonly<{
  code: string;
  period: string;
  statsForPeriod: any[] | null;
  onClose: () => void;
}>) {
  const { t, tRich, locale, currencyName, currencyNameInPhrase } = useI18n();
  const { getCachedHistory, fetchHistory } = useCurrency();
  const [data, setData] = useState<any>(() => getCachedHistory(code, period) ?? null);
  const [error, setError] = useState(false);
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  // Panel jadval ostida, ko'pincha ko'rinadigan maydondan tashqarida
  // ochiladi (720px balandlikdagi oynada ~6% ko'rinadi) — ochilganda
  // stol ustiga tortamiz, aks holda bosish "hech narsa bo'lmadi" tuyuladi.
  // `data` bog'liqligi shart: mount paytida panel hali qisqa (loading),
  // kontent kelgach cho'ziladi va pozitsiya o'zgaradi.
  useEffect(() => {
    panelRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [code, data]);

  useEffect(() => {
    let cancelled = false;
    setError(false);
    setHoverIndex(null);
    const cached = getCachedHistory(code, period);
    if (cached) {
      setData(cached);
      return;
    }
    setData(null);
    fetchHistory(code, period)
      .then((d: any) => {
        if (!cancelled) setData(d);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });
    return () => {
      cancelled = true;
    };
  }, [code, period]);

  const wrapRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState<{ w: number; h: number } | null>(null);

  // Geometriyani real kenglikda quramiz: SVG viewBox qafas bilan 1:1
  // mos tushadi va chiziqlar/matnlar cho'zilmaydi (responsive chart).
  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const ro = new ResizeObserver(entries => {
      const r = entries[0].contentRect;
      if (r.width < 1 || r.height < 1) return;
      const next = { w: Math.round(r.width), h: Math.round(r.height) };
      setSize(prev => (prev?.w === next.w && prev?.h === next.h ? prev : next));
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [data]);

  const geometry = useMemo(
    () => (data?.points.length ? buildChartGeometry(data.points, size?.w, size?.h) : null),
    [data, size],
  );

  const stat = useMemo(() => {
    if (!data?.points.length) return null;
    const cachedStat = (statsForPeriod ?? []).find((s: any) => s.code === code);
    return cachedStat ?? statsFromPoints(data.points);
  }, [data, statsForPeriod, code]);

  const name = currencyNameInPhrase(code);

  function handleMouseMove(e: React.MouseEvent<SVGRectElement>) {
    if (!geometry || !svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const scaleX = geometry.w / rect.width;
    const localX = (e.clientX - rect.left) * scaleX;
    const index = geometry.stepX > 0 ? Math.round((localX - geometry.padL) / geometry.stepX) : 0;
    setHoverIndex(Math.min(geometry.xy.length - 1, Math.max(0, index)));
  }

  const hoverPoint = hoverIndex !== null && geometry ? geometry.xy[hoverIndex] : null;

  let loadingNote: React.ReactNode = null;
  if (error) {
    loadingNote = <div className="mpl-chart-loading">{t("mpl_chart_load_error")}</div>;
  } else if (!data) {
    loadingNote = <div className="mpl-chart-loading">{t("mpl_loading")}</div>;
  } else if (!data.points.length) {
    loadingNote = <div className="mpl-chart-loading">{t("mpl_chart_no_data")}</div>;
  }

  return (
    <div className="mpl-chart-panel" ref={panelRef}>
      <div className="mpl-chart-head">
        <div className="mpl-chart-title">
          <span className="mpl-chart-code">
            {currencyName(code)} ({code})
          </span>
          <span className="mpl-chart-current">
            {stat && (
              <>
                {fmtRate(stat.current, locale)} {t("sum_currency")}{" "}
                <ChangeBadge changePct={stat.change_pct} />
              </>
            )}
          </span>
        </div>
        <button className="mpl-chart-close" title={t("mpl_chart_close_title")} onClick={onClose}>
          ✕
        </button>
      </div>
      <div className="mpl-chart-body">
        {loadingNote ??
          (() => {
            const isUp = stat.change_pct >= 0;
            let dirWord = t("dir_flat");
            if (stat.change_pct > 0) {
              dirWord = t("dir_up");
            } else if (stat.change_pct < 0) {
              dirWord = t("dir_down");
            }
            const changePctSign = stat.change_pct > 0 ? "+" : "";
            const changePctSuffix =
              stat.change_pct !== 0 ? ` (${changePctSign}${stat.change_pct.toFixed(2)}%)` : "";
            const sentenceVars = {
              period: periodPhrase(period, t),
              name,
              min: fmtRate(stat.min, locale),
              max: fmtRate(stat.max, locale),
              current: fmtRate(stat.current, locale),
              dir: dirWord,
              changePct: changePctSuffix,
            };
            const chartColor = isUp ? "#16a34a" : "var(--accent)";
            const linePoints = geometry!.xy
              .map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`)
              .join(" ");
            const baseY = (geometry!.padT + geometry!.innerH).toFixed(1);
            const areaPoints = `${geometry!.padL.toFixed(1)},${baseY} ${linePoints} ${(geometry!.padL + geometry!.innerW).toFixed(1)},${baseY}`;

            return (
              <>
                <p className="mpl-chart-sentence">{tRich("mpl_chart_sentence", sentenceVars)}</p>
                <div className="mpl-chart-stats">
                  <div className="mpl-chart-stat">
                    <span className="stat-label">{t("mpl_col_min")}</span>
                    <span className="stat-value">{fmtRate(stat.min, locale)}</span>
                  </div>
                  <div className="mpl-chart-stat">
                    <span className="stat-label">{t("mpl_col_avg")}</span>
                    <span className="stat-value">{fmtRate(stat.avg, locale)}</span>
                  </div>
                  <div className="mpl-chart-stat">
                    <span className="stat-label">{t("mpl_col_max")}</span>
                    <span className="stat-value">{fmtRate(stat.max, locale)}</span>
                  </div>
                </div>
                <p className="mpl-chart-section-label">{t("mpl_chart_section_trend")}</p>
                <div
                  ref={wrapRef}
                  className="mpl-chart-svg-wrap"
                  style={{ "--chart-color": chartColor } as React.CSSProperties}>
                  <svg
                    ref={svgRef}
                    className="mpl-chart-svg"
                    viewBox={`0 0 ${geometry!.w} ${geometry!.h}`}
                    preserveAspectRatio="none">
                    <defs>
                      <linearGradient id="mplChartGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" className="mpl-grad-start" />
                        <stop offset="100%" className="mpl-grad-end" />
                      </linearGradient>
                    </defs>
                    {geometry!.yTicks.map(tick => (
                      <g key={tick.value}>
                        <line
                          className="mpl-chart-grid"
                          x1={geometry!.padL}
                          y1={tick.y.toFixed(1)}
                          x2={geometry!.padL + geometry!.innerW}
                          y2={tick.y.toFixed(1)}
                        />
                        <text
                          className="mpl-chart-axis-label"
                          x={geometry!.padL - 8}
                          y={(tick.y + 4).toFixed(1)}
                          textAnchor="end">
                          {fmtRate(tick.value, locale)}
                        </text>
                      </g>
                    ))}
                    <polygon className="mpl-chart-area" points={areaPoints} />
                    <polyline className="mpl-chart-line" points={linePoints} />
                    {geometry!.xTicks.map(tick => (
                      <text
                        key={`${tick.date}-${tick.anchor}`}
                        className="mpl-chart-axis-label"
                        x={tick.x.toFixed(1)}
                        y={geometry!.h - 6}
                        textAnchor={tick.anchor as any}>
                        {fmtDateShort(tick.date)}
                      </text>
                    ))}
                    {hoverPoint && (
                      <>
                        <line
                          className="mpl-chart-hover-line"
                          x1={hoverPoint.x}
                          y1={geometry!.padT}
                          x2={hoverPoint.x}
                          y2={geometry!.padT + geometry!.innerH}
                          style={{ opacity: 1 }}
                        />
                        <circle
                          className="mpl-chart-hover-dot"
                          r="4"
                          cx={hoverPoint.x}
                          cy={hoverPoint.y}
                          style={{ opacity: 1 }}
                        />
                      </>
                    )}
                    <rect
                      x={geometry!.padL}
                      y="0"
                      width={Math.max(geometry!.innerW, 1)}
                      height={geometry!.h}
                      fill="transparent"
                      onMouseMove={handleMouseMove}
                      onMouseLeave={() => setHoverIndex(null)}
                    />
                  </svg>
                  {hoverPoint && svgRef.current && (
                    <div
                      className="mpl-chart-tooltip"
                      style={{
                        opacity: 1,
                        left: `${(hoverPoint.x / geometry!.w) * svgRef.current.getBoundingClientRect().width}px`,
                        top: `${(hoverPoint.y / geometry!.h) * svgRef.current.getBoundingClientRect().height - 8}px`,
                      }}>
                      <div className="tt-date">{fmtDate(hoverPoint.date)}</div>
                      <div className="tt-value">{fmtRate(hoverPoint.value, locale)}</div>
                    </div>
                  )}
                </div>
                <div className="mpl-chart-legend">
                  <span className="legend-dot" style={{ background: chartColor }} />
                  {t("currency_legend", { name })}
                </div>
                <p className="mpl-chart-hint-text">{t("mpl_chart_hint_hover")}</p>
              </>
            );
          })()}
      </div>
    </div>
  );
}
