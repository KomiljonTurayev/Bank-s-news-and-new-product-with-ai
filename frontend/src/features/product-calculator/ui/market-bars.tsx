import type { ReactNode } from "react";

import { useI18n } from "@/shared/lib/i18n/i18n-context";

// Mahsulot turi bo'yicha bank taqqoslash diagrammasi — bizning
// mahsulotimizni bozordagi eng yaxshi bank takliflari qatoriga
// (yo'nalishga qarab: kredit — pastroq, boshqalari — yuqoriroq stavka
// yaxshi) joylashtirib, gorizontal chiziqlar bilan solishtiradi.
export default function MarketBars({
  product,
  analysis,
}: Readonly<{ product: any; analysis: any }>) {
  const { t, safeUrl } = useI18n();
  if (!analysis.market_sample.length) return null;

  const lowerIsBetter = product.product_type === "credit";
  const ourEntry = {
    bank_name: product.bank_name || t("your_product_fallback"),
    rate: product.rate,
    isOurs: true,
    url: null,
  };
  const combined = [
    ...analysis.market_sample.map((s: any) => ({
      bank_name: s.bank_name,
      rate: s.rate,
      isOurs: false,
      url: s.url,
    })),
    ourEntry,
  ];
  combined.sort((x, y) => (lowerIsBetter ? x.rate - y.rate : y.rate - x.rate));
  const maxRate = Math.max(...combined.map(e => e.rate)) || 1;

  return (
    <div className="pp-card">
      <div className="pp-card-label">{t("market_bars_hint")}</div>
      <div className="pp-bars">
        {combined.map(e => {
          const pct = Math.max(4, (e.rate / maxRate) * 100).toFixed(1);
          const safe = safeUrl(e.url);
          let label: ReactNode;
          if (e.isOurs) {
            label = <span className="pp-bar-label">{e.bank_name}</span>;
          } else if (safe) {
            label = (
              <a
                className="pp-bar-label pp-bar-link"
                href={safe}
                target="_blank"
                rel="noopener noreferrer">
                {e.bank_name} ↗
              </a>
            );
          } else {
            label = <span className="pp-bar-label">{e.bank_name}</span>;
          }
          return (
            <div
              className={`pp-bar-row${e.isOurs ? " ours" : ""}`}
              key={e.isOurs ? "ours" : `${e.bank_name}|${e.rate}|${e.url ?? ""}`}>
              {label}
              <div className="pp-bar-track">
                <div className="pp-bar-fill" style={{ width: `${pct}%` }} />
              </div>
              <span className="pp-bar-value">{e.rate}%</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
