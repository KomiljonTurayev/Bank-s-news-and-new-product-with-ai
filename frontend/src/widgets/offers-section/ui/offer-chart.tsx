import { useI18n } from "@/shared/lib/i18n/i18n-context";
import { useOffers, useRateFormat } from "@/entities/offer";
import { matchesFilters } from "@/shared/lib/matches-filters";
import OtherFields from "@/shared/ui/other-fields";
import SourceLink from "@/shared/ui/source-link";

const COMPARE_DETAIL_SKIP_FIELDS = ["bank_name", "name", "source", "url", "Muddat", "term"];

const CHART_HINT_KEYS: Record<string, string> = {
  deposit: "chart_hint_deposit",
  credit: "chart_hint_credit",
  card: "chart_hint_card",
  investment: "chart_hint_investment",
  currency: "chart_hint_currency",
};

// Har bir bank uchun eng maqbul (foiz bo'yicha) bitta yozuvni tanlaydi va
// banklarni shu bo'yicha eng qulaydan eng nomaqbulgacha tartiblaydi —
// foydalanuvchi grafikni bir qarashda o'qiy olishi uchun.
export default function OfferChart() {
  const { t, translateFieldValue } = useI18n();
  const { directory, byBank, product, search, compareSet } = useOffers();
  const { extractRate, sortScore } = useRateFormat();

  const hint = CHART_HINT_KEYS[product] ? t(CHART_HINT_KEYS[product]) : "";

  const banks = Array.from(directory, ([code, name]) => ({ code, name }))
    .filter((b: any) => matchesFilters(b.code, b.name, { search, compareSet }))
    .map((b: any) => {
      const records = byBank.get(b.code) ?? [];
      if (!records.length) return null;
      // Debet karta kabi foizsiz mahsulotlar uchun ham banklar ko'rinishda
      // qolishi kerak — faqat "eng qulay" reytingi ular uchun ishlamaydi.
      let best: any = null;
      for (const record of records) {
        const percent = extractRate(record.data).percent;
        const score = percent === null ? null : sortScore(record, "best");
        if (best === null || (score !== null && (best.score === null || score > best.score))) {
          best = { record, percent, score };
        }
      }
      return { ...b, ...best };
    })
    .filter(Boolean)
    .sort((a: any, b: any) => (b.score ?? -Infinity) - (a.score ?? -Infinity));

  if (!banks.length) {
    return (
      <section className="chart-view">
        <p className="chart-hint">{hint}</p>
        <div className="chart-rows">
          <div className="loading">{t("chart_no_data")}</div>
        </div>
      </section>
    );
  }

  const rowDefs = [
    {
      label: t("compare_col_product"),
      render: (b: any) => {
        const data = b.record.data;
        if (data.name !== undefined && data.name !== null) return data.name;
        if (!data.code) return "—";
        const sideSuffix = data.side ? " · " + translateFieldValue(data.side) : "";
        return `${data.code}${sideSuffix}`;
      },
    },
    {
      label: t("compare_col_rate"),
      render: (b: any) => <span className="rate-cell">{extractRate(b.record.data).label}</span>,
    },
    {
      label: t("compare_col_term"),
      render: (b: any) => translateFieldValue(b.record.data.Muddat ?? b.record.data.term ?? "—"),
    },
    {
      label: t("compare_col_other"),
      render: (b: any) => {
        const data = b.record.data;
        const skip = new Set([
          ...COMPARE_DETAIL_SKIP_FIELDS,
          "code",
          "side",
          "date",
          extractRate(data).key,
        ]);
        return <OtherFields data={data} skipKeys={skip} fallback="—" />;
      },
    },
    { label: "", render: (b: any) => <SourceLink url={b.record.data.url} /> },
  ];

  return (
    <section className="chart-view">
      <p className="chart-hint">{hint}</p>
      <div className="chart-rows">
        <table className="matrix-table">
          <thead>
            <tr>
              <th className="matrix-row-label" />
              {banks.map((b: any, i: number) => (
                <th className="matrix-bank-col" key={b.code}>
                  <div className="matrix-bank-name">{b.name}</div>
                  {i === 0 && b.score !== null && (
                    <span className="chart-badge">{t("chart_best_badge")}</span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rowDefs.map(row => (
              <tr key={row.label}>
                <th className="matrix-row-label">{row.label}</th>
                {banks.map((b: any) => (
                  <td key={b.code}>{row.render(b)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
