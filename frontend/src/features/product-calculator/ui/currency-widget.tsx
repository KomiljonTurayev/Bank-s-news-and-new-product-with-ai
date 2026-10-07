import { useI18n } from "@/shared/lib/i18n/i18n-context";
import { fmtRate } from "@/shared/lib/format";
import Sparkline from "@/shared/ui/sparkline";
import ChangeBadge from "@/shared/ui/change-badge";

// Mahsulot chet el valyutasida bo'lsa (USD/EUR), cbu.uz arxividagi shu
// valyutaning so'nggi 30 kunlik tendensiyasini ham ko'rsatamiz.
export default function CurrencyWidget({ code, entry }: Readonly<{ code: string; entry: any }>) {
  const { t, locale, currencyNameInPhrase } = useI18n();
  const name = currencyNameInPhrase(code);
  return (
    <div className="pp-card">
      <div className="pp-card-label">{t("currency_widget_title", { name })}</div>
      <div className="pr-currency-widget">
        <Sparkline values={entry.sparkline} />
        <div className="cw-info">
          <span className="cw-rate">
            {fmtRate(entry.current, locale)} {t("sum_currency")}
          </span>
          <ChangeBadge changePct={entry.change_pct} />
        </div>
      </div>
    </div>
  );
}
