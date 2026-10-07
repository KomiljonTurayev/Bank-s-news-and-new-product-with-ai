import { useI18n } from "@/shared/lib/i18n/i18n-context";
import { TERM_BUCKETS, matchesOfferFilters, useOffers } from "@/entities/offer";

// Batafsil filtrlar: har guruhda chip'lar, yonida shu tanlov bilan nechta
// taklif qolishi. Hisob boshqa faol filtrlar hisobga olingan holda
// chiqadi — 0 ta qoladigan variant ko'rsatilmaydi.

const CREDIT_CATEGORIES = ["Ipoteka", "Avtokredit", "Iste'mol krediti", "Mikroqarz", "Ta'lim krediti", "Overdraft", "Boshqa"];
const CURRENCIES = ["UZS", "USD", "EUR"];
const NETWORKS = ["Humo", "Uzcard", "Visa", "Mastercard", "UnionPay", "Mir"];

type Option = { value: string; label: string };
type Group = { key: string; title: string; options: Option[] };

// "extra" guruhidagi har bir variant o'z kaliti bilan (online/kids) saqlanadi.
const filterKey = (group: string, value: string) => (group === "extra" ? value : group);
const filterValue = (group: string, value: string) => (group === "extra" ? "1" : value);

export default function FilterBar() {
  const { t } = useI18n();
  const { product, allRows, filters, setFilter, clearFilters } = useOffers();

  if (!["deposit", "credit", "card", "investment"].includes(product) || allRows.length === 0) return null;

  const groups: Group[] = [];
  if (product === "credit") {
    groups.push({
      key: "category",
      title: t("flt_credit_type"),
      options: CREDIT_CATEGORIES.map(c => ({ value: c, label: t(`flt_cat_${c}`) })),
    });
  }
  if (product === "card") {
    groups.push(
      {
        key: "card_type",
        title: t("flt_card_type"),
        options: [
          { value: "debit", label: t("flt_card_debit") },
          { value: "credit", label: t("flt_card_credit") },
        ],
      },
      { key: "network", title: t("flt_network"), options: NETWORKS.map(n => ({ value: n, label: n })) },
    );
  }
  const buckets = TERM_BUCKETS[product];
  if (buckets) {
    groups.push({
      key: "term",
      title: t("flt_term"),
      options: buckets.map(b => ({
        value: b.key,
        label: b.to == null ? t("flt_term_from", { from: b.from }) : t("flt_term_range", { from: b.from, to: b.to }),
      })),
    });
  }
  if (product === "deposit") {
    groups.push({
      key: "extra",
      title: t("flt_features"),
      options: [
        { value: "online", label: t("flt_online") },
        { value: "kids", label: t("flt_kids") },
      ],
    });
  }
  groups.push({ key: "currency", title: t("flt_currency"), options: CURRENCIES.map(c => ({ value: c, label: c })) });

  function countFor(group: string, value: string) {
    const next = { ...filters, [filterKey(group, value)]: filterValue(group, value) };
    return allRows.filter((row: any) => matchesOfferFilters(row, product, next)).length;
  }

  const activeCount = Object.keys(filters).length;

  return (
    <div className="filter-bar">
      {groups.map(group => {
        const options = group.options
          .map(o => ({ ...o, count: countFor(group.key, o.value) }))
          .filter(o => o.count > 0 || filters[filterKey(group.key, o.value)] !== undefined);
        // Bitta variantli guruh (masalan faqat UZS) tanlov bermaydi.
        if (options.length === 0 || (options.length < 2 && group.key !== "extra")) return null;
        return (
          <div className="filter-group" key={group.key} role="group" aria-label={group.title}>
            <span className="filter-title">{group.title}</span>
            <div className="filter-chips">
              {options.map(o => {
                const key = filterKey(group.key, o.value);
                const value = filterValue(group.key, o.value);
                const active = filters[key] === value;
                return (
                  <button
                    key={o.value}
                    type="button"
                    className={`filter-chip${active ? " active" : ""}`}
                    aria-pressed={active}
                    onClick={() => setFilter(key, value)}>
                    {o.label}
                    <span className="filter-count">{o.count}</span>
                  </button>
                );
              })}
            </div>
          </div>
        );
      })}
      {activeCount > 0 && (
        <button type="button" className="filter-clear" onClick={clearFilters}>
          {t("flt_clear", { n: activeCount })}
        </button>
      )}
    </div>
  );
}
