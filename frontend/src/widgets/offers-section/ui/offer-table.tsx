import { useI18n } from "@/shared/lib/i18n/i18n-context";
import { recordKey, useOffers, useRateFormat } from "@/entities/offer";
import { matchesFilters } from "@/shared/lib/matches-filters";
import OtherFields from "@/shared/ui/other-fields";

const COMPARE_DETAIL_SKIP_FIELDS = ["bank_name", "name", "source", "url", "Muddat", "term"];

export default function OfferTable() {
  const { t, translateFieldValue, safeUrl } = useI18n();
  const { rows, directory, sort, search, compareSet } = useOffers();
  const { extractRate, sortScore } = useRateFormat();

  let items = rows
    .map((row: any) => ({
      bank: directory.get(row.bank_code) ?? row.bank_code,
      row,
      rate: extractRate(row.data),
    }))
    .filter((item: any) => matchesFilters(item.row.bank_code, item.bank, { search, compareSet }));

  items.sort((a: any, b: any) => {
    if (sort === "bank_az") return a.bank.localeCompare(b.bank);
    const sa = sortScore(a.row, sort);
    const sb = sortScore(b.row, sort);
    if (sort === "rate_asc") return (sa ?? Infinity) - (sb ?? Infinity);
    return (sb ?? -Infinity) - (sa ?? -Infinity);
  });

  return (
    <section className="compare-table-wrap">
      <table className="compare-table">
        <thead>
          <tr>
            <th>{t("compare_col_bank")}</th>
            <th>{t("compare_col_product")}</th>
            <th>{t("compare_col_rate")}</th>
            <th>{t("compare_col_term")}</th>
            <th>{t("compare_col_other")}</th>
          </tr>
        </thead>
        <tbody>
          {items.length === 0 ? (
            <tr>
              <td colSpan={5} className="loading">
                {t("bank_grid_not_found")}
              </td>
            </tr>
          ) : (
            items.map(({ bank, row, rate }: any) => {
              const data = row.data;
              const skip = new Set(COMPARE_DETAIL_SKIP_FIELDS);
              if (rate.hideFromDetails && rate.key) skip.add(rate.key);
              // Uchi-ichma-uch uch tomonlama: avval `side` qo'shimchasi, so'ng
              // kod/nom tanlanadi (natija oldingidek).
              const sideSuffix = data.side ? " · " + translateFieldValue(data.side) : "";
              const nameLabel = data.name ?? (data.code ? `${data.code}${sideSuffix}` : "—");
              const safe = safeUrl(data.url);
              return (
                <tr key={recordKey(row)}>
                  <td>{bank}</td>
                  <td>
                    {safe ? (
                      <a href={safe} target="_blank" rel="noopener noreferrer">
                        {nameLabel} ↗
                      </a>
                    ) : (
                      nameLabel
                    )}
                  </td>
                  <td className="rate-cell">{rate.label}</td>
                  <td>{translateFieldValue(data.Muddat ?? data.term ?? "—")}</td>
                  <td className="other-cell">
                    <OtherFields data={data} skipKeys={skip} fallback="—" />
                  </td>
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </section>
  );
}
