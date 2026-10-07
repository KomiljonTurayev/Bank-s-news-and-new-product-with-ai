import { useI18n } from "@/shared/lib/i18n/i18n-context";
import { useOffers } from "@/entities/offer";
import { formatTime } from "@/shared/lib/format";

const iconProps = {
  viewBox: "0 0 24 24",
  width: 16,
  height: 16,
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": true,
} as const;

const VIEWS = [
  {
    key: "cards",
    titleKey: "view_cards_title",
    icon: (
      <svg {...iconProps}>
        <rect x="3.5" y="3.5" width="7.5" height="7.5" rx="1.5" />
        <rect x="13" y="3.5" width="7.5" height="7.5" rx="1.5" />
        <rect x="3.5" y="13" width="7.5" height="7.5" rx="1.5" />
        <rect x="13" y="13" width="7.5" height="7.5" rx="1.5" />
      </svg>
    ),
  },
  {
    key: "table",
    titleKey: "view_table_title",
    icon: (
      <svg {...iconProps}>
        <path d="M3.5 6h17M3.5 12h17M3.5 18h17" />
      </svg>
    ),
  },
  {
    key: "chart",
    titleKey: "view_chart_title",
    icon: (
      <svg {...iconProps}>
        <path d="M4 20V10M10 20V4M16 20v-8M21 20H3" />
      </svg>
    ),
  },
];

export default function Toolbar() {
  const { t, locale } = useI18n();
  const { search, setSearch, sort, setSort, view, setView, latestFetch } = useOffers();

  return (
    <div className="toolbar">
      <input
        className="search-input"
        type="search"
        placeholder={t("search_placeholder")}
        value={search}
        onChange={e => setSearch(e.target.value)}
      />
      <select className="sort-select" value={sort} onChange={e => setSort(e.target.value)}>
        <option value="best">{t("sort_best")}</option>
        <option value="rate_desc">{t("sort_rate_desc")}</option>
        <option value="rate_asc">{t("sort_rate_asc")}</option>
        <option value="bank_az">{t("sort_bank_az")}</option>
      </select>
      <div className="view-toggle">
        {VIEWS.map(v => (
          <button
            key={v.key}
            className={`view-btn${view === v.key ? " active" : ""}`}
            title={t(v.titleKey)}
            onClick={() => setView(v.key)}>
            {v.icon}
          </button>
        ))}
      </div>
      <span className="updated-note">
        {latestFetch ? t("updated_note", { time: formatTime(latestFetch, locale) }) : ""}
      </span>
    </div>
  );
}
