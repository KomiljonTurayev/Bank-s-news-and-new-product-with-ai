import { useI18n } from "@/shared/lib/i18n/i18n-context";
import { useOffers } from "@/entities/offer";

const TABS = [
  { key: "deposit", labelKey: "tab_deposit" },
  { key: "credit", labelKey: "tab_credit" },
  { key: "card", labelKey: "tab_card" },
  { key: "investment", labelKey: "tab_investment" },
  { key: "currency", labelKey: "tab_currency" },
];

export default function Tabs() {
  const { t } = useI18n();
  const { product, setProduct } = useOffers();

  return (
    <nav className="tabs">
      {TABS.map(tab => (
        <button
          key={tab.key}
          className={`tab-btn${product === tab.key ? " active" : ""}`}
          onClick={() => setProduct(tab.key)}>
          {t(tab.labelKey)}
        </button>
      ))}
    </nav>
  );
}
