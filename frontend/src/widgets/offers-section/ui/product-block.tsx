import { useI18n } from "@/shared/lib/i18n/i18n-context";
import { useCurrency } from "@/entities/currency";
import { useRateFormat } from "@/entities/offer";
import DetailValue from "@/shared/ui/detail-value";
import ChangeBadge from "@/shared/ui/change-badge";
import SourceLink from "@/shared/ui/source-link";

const HIDDEN_FIELDS = new Set(["sample", "bank_name", "source", "url"]);

// Bitta bank kartasi ichida bir nechta mahsulot bo'lsa, har biri o'z
// chegarasi bilan alohida blok sifatida chiqadi — aks holda maydonlar
// bir-biriga qo'shilib, qaysi qiymat qaysi mahsulotga tegishli ekani
// ko'rinmay qoladi.
export default function ProductBlock({ record }: Readonly<{ record: any }>) {
  const { t, translateFieldKey, translateFieldValue, locale } = useI18n();
  const { changeByCode } = useCurrency();
  const { extractRate } = useRateFormat();
  const data = record.data;

  if (record.product_type === "currency") {
    const title = data.side
      ? `${data.code ?? t("currency_fallback")} · ${translateFieldValue(data.side)}`
      : (data.code ?? t("currency_fallback"));
    const change = changeByCode[data.code];
    return (
      <div className="product-block">
        <div className="product-head">
          <span className="product-name">{title}</span>
          <span className="product-rate">
            {Number(data.rate).toLocaleString(locale)} {t("sum_currency")}
          </span>
        </div>
        <div className="product-details">
          {change !== undefined && (
            <div className="detail">
              <span>{t("currency_period_change_label")}</span>
              <ChangeBadge changePct={change} />
            </div>
          )}
          {data.date && (
            <div className="detail">
              <span>{t("date_label")}</span>
              <span>{data.date}</span>
            </div>
          )}
        </div>
        <SourceLink url={data.url} />
      </div>
    );
  }

  const rate = extractRate(data);
  const skip = new Set([...HIDDEN_FIELDS, "name"]);
  if (rate.hideFromDetails && rate.key) skip.add(rate.key);
  const details = Object.entries(data).filter(([key]) => !skip.has(key));

  return (
    <div className="product-block">
      <div className="product-head">
        <span className="product-name">{data.name ?? t("product_fallback_name")}</span>
        {rate.percent !== null && <span className="product-rate">{rate.label}</span>}
      </div>
      {details.length > 0 && (
        <div className="product-details">
          {details.map(([key, value]) => (
            <div className="detail" key={key}>
              <span>{translateFieldKey(key)}</span>
              <span>
                <DetailValue value={value} />
              </span>
            </div>
          ))}
        </div>
      )}
      <SourceLink url={data.url} />
    </div>
  );
}
