import { useEffect, useState } from "react";
import { notifications } from "@mantine/notifications";

import { useI18n } from "@/shared/lib/i18n/i18n-context";
import { useOpenScreen } from "@/shared/lib/nav/use-open-screen";
import { fetchJSON, apiFetch, invalidateJsonCache } from "@/shared/api/base";
import { buildBankDirectory, extractRate, extractTermMonths } from "@/entities/offer";
import { useMeta } from "@/entities/meta";
import SourceLink from "@/shared/ui/source-link";

import { useAmountField } from "../lib/use-amount-field";
import { validateProductForm, NP_TERM_MAX_MONTHS } from "../lib/product-validation";
import { CAR_BRANDS } from "../lib/car-brands";

const CATEGORY_OPTIONS = [
  { value: "Iste'mol krediti", key: "cat_consumer" },
  { value: "Ipoteka", key: "cat_mortgage" },
  { value: "Avtokredit", key: "cat_auto" },
  { value: "Ta'lim krediti", key: "cat_education" },
  { value: "Overdraft", key: "cat_overdraft" },
  { value: "Mikroqarz", key: "cat_micro" },
];

// Ba'zi kredit turlari tanlanganda qo'shimcha sub-turi tanlash maydoni(lari)
// ko'rinadi. Bozor ma'lumotlari (BankRate) bu darajada mayda toifaga
// bo'linmagani uchun bu tanlov "category"ni o'zgartirmaydi — o'rniga
// tanlangan qiymat(lar) "Maqsadi" maydoniga qo'shiladi (composePurpose()).
const SUB_TYPE_FIELDS_BY_CATEGORY: Record<string, string[]> = {
  Avtokredit: ["carMarketType", "carBrand"],
  Ipoteka: ["mortgageType"],
  "Iste'mol krediti": ["consumerType"],
  Mikroqarz: ["microType"],
  "Ta'lim krediti": ["educationType"],
};

// Son maydonlariga klaviatura filtrini qo'yadi — holatga bog'liq emas, shuning
// uchun hook tashqarisida (modul darajasida) ta'riflanadi.
function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
  if (e.key === "-" || e.key === "+" || e.key === "e" || e.key === "E") e.preventDefault();
}

function useNumberField(max: number) {
  const [value, setValue] = useState("");
  function onChange(e: React.ChangeEvent<HTMLInputElement>) {
    const v = e.target.value;
    if (v === "") {
      setValue("");
      return;
    }
    const num = Number(v);
    if (num < 0) setValue("0");
    else if (Number.isFinite(max) && num > max) setValue(String(max));
    else setValue(v);
  }
  return { value, onChange, onKeyDown, setValue };
}

// Xato javobdagi FastAPI `detail` maydonini o'qib beradi; javob JSON bo'lmasa
// null qaytadi — chaqiruvchi tomonda status kodi fallback bo'ladi.
async function readErrorDetail(response: Response) {
  try {
    const body = await response.json();
    return Array.isArray(body.detail) ? body.detail[0]?.msg : body.detail;
  } catch {
    // javob JSON emas — umumiy xabar bilan davom etiladi
    return null;
  }
}

async function applySaveResult(
  response: Response,
  editId: number | undefined,
  t: (key: string, vars?: any) => string,
  goBackOr: (path: string) => void,
  open: (path: string) => void,
) {
  // Saqlangan ro'yxat/natija endi eskirgan — keshdan o'sha mahsulot
  // bo'yicha javoblarni tushirib tashlaymiz.
  invalidateJsonCache("/api/products");
  if (editId !== undefined) {
    notifications.show({
      title: t("update_success_title"),
      message: t("update_success_msg"),
      color: "green",
      autoClose: 4500,
    });
    // Natija ekrani qayta mount bo'lib tahlilni yangi shartlar bo'yicha
    // boshdan so'raydi.
    goBackOr(`/products/${editId}`);
    return;
  }
  const created = await response.json();
  notifications.show({
    title: t("create_success_title"),
    message: t("create_success_msg"),
    color: "green",
    autoClose: 4500,
  });
  open(`/products/${created.id}`);
}

function saveErrorMessage(err: any, t: (key: string, vars?: any) => string): string {
  if (typeof err.message === "string" && err.message && !/^\d+$/.test(err.message)) {
    return err.message;
  }
  return t("save_error_generic");
}

export default function ProductForm({ editId }: Readonly<{ editId?: number }>) {
  const { t, locale } = useI18n();
  const { banks } = useMeta();
  const { open, goBackOr } = useOpenScreen();

  const [name, setName] = useState("");
  const [category, setCategory] = useState(CATEGORY_OPTIONS[0].value);
  const [carMarketType, setCarMarketType] = useState("");
  const [carBrand, setCarBrand] = useState("");
  const [mortgageType, setMortgageType] = useState("");
  const [consumerType, setConsumerType] = useState("");
  const [microType, setMicroType] = useState("");
  const [educationType, setEducationType] = useState("");
  const [bank, setBank] = useState("");
  const [purpose, setPurpose] = useState("");
  const [currency, setCurrency] = useState("UZS");

  const minAmount = useAmountField();
  const maxAmount = useAmountField();
  const rate = useNumberField(100);
  const term = useNumberField(NP_TERM_MAX_MONTHS);
  const initialPayment = useNumberField(100);

  const [copyFromIndex, setCopyFromIndex] = useState("");
  const [copySourceUrl, setCopySourceUrl] = useState<string | null>(null);
  const [existingOffers, setExistingOffers] = useState<any[] | null>(null);
  const [existingOffersError, setExistingOffersError] = useState(false);

  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const isEdit = editId !== undefined;
  const [loadingProduct, setLoadingProduct] = useState(isEdit);
  const [loadError, setLoadError] = useState(false);

  // Tahrirlash rejimi: bazada saqlangan ma'lumotlar formaga qaytariladi.
  // Quyi-tur maydonlarida (masalan avtomobil bozori/brendi) alohida qiymat
  // saqlanmaydi — ular "Maqsadi" qatorining boshiga yozilgan holda qaytadi,
  // shu bois qator o'zgartirilmagan holicha saqlanib qoladi.
  useEffect(() => {
    if (editId === undefined) return;
    let cancelled = false;
    setLoadingProduct(true);
    setLoadError(false);
    fetchJSON(`/api/products/${editId}`)
      .then((p: any) => {
        if (cancelled) return;
        setName(p.name ?? "");
        if (CATEGORY_OPTIONS.some(o => o.value === p.category)) setCategory(p.category);
        setBank(p.bank_name ?? "");
        setPurpose(p.purpose ?? "");
        setCurrency(p.currency ?? "UZS");
        rate.setValue(p.rate === null ? "" : String(p.rate));
        term.setValue(p.term_months === null ? "" : String(p.term_months));
        minAmount.reset(p.min_amount === null ? "" : String(p.min_amount));
        maxAmount.reset(p.max_amount === null ? "" : String(p.max_amount));
        initialPayment.setValue(
          p.initial_payment_pct === null ? "" : String(p.initial_payment_pct),
        );
        setLoadingProduct(false);
      })
      .catch(() => {
        if (cancelled) return;
        setLoadError(true);
        setLoadingProduct(false);
      });
    return () => {
      cancelled = true;
    };
  }, [editId]);

  useEffect(() => {
    if (editId !== undefined) return;
    setExistingOffersError(false);
    fetchJSON("/api/rates/latest?product_type=credit")
      .then(rows => {
        const directory = buildBankDirectory(rows, banks);
        const offers = rows
          .map((row: any) => ({
            row,
            bankName: directory.get(row.bank_code) ?? row.bank_code,
            rate: extractRate(row.data, { t, locale }),
          }))
          .filter((o: any) => o.rate.percent !== null)
          .sort(
            (a: any, b: any) =>
              a.bankName.localeCompare(b.bankName) || a.rate.percent - b.rate.percent,
          );
        setExistingOffers(offers);
      })
      .catch(() => setExistingOffersError(true));
  }, []);

  const activeSubFields = SUB_TYPE_FIELDS_BY_CATEGORY[category] ?? [];

  function resetSubTypeFields() {
    setCarMarketType("");
    setCarBrand("");
    setMortgageType("");
    setConsumerType("");
    setMicroType("");
    setEducationType("");
  }

  function handleCategoryChange(next: string) {
    setCategory(next);
    resetSubTypeFields();
  }

  function handleCopyFromChange(indexStr: string) {
    setCopyFromIndex(indexStr);
    setCopySourceUrl(null);
    if (indexStr === "" || !existingOffers) return;
    const { row, bankName, rate: offerRate } = existingOffers[Number.parseInt(indexStr, 10)];
    setBank(bankName);
    setName(row.data.name ?? "");
    rate.setValue(offerRate.percent !== null ? String(offerRate.percent) : "");

    const offerCategory = row.data.category;
    if (offerCategory && CATEGORY_OPTIONS.some(o => o.value === offerCategory)) {
      setCategory(offerCategory);
    }
    resetSubTypeFields();

    // Haqiqiy banklarning ba'zi (masalan ipoteka) takliflari 240 oydan
    // uzoqroq bo'lishi mumkin — formaning o'zi shuncha bilan cheklangani
    // uchun, nusxalanganda ham shu chegaraga moslab qisqartiramiz.
    const termMonths = extractTermMonths(row.data);
    if (termMonths !== null) term.setValue(String(Math.min(termMonths, NP_TERM_MAX_MONTHS)));

    if (row.data.url) setCopySourceUrl(row.data.url);
  }

  function composePurpose() {
    const base = purpose.trim();
    const fieldValues: Record<string, string> = {
      carMarketType,
      carBrand,
      mortgageType,
      consumerType,
      microType,
      educationType,
    };
    const extra = activeSubFields
      .map(fieldId => fieldValues[fieldId])
      .filter(Boolean)
      .join(", ");
    if (!extra) return base || null;
    return base ? `${extra} — ${base}` : extra;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);

    const payload = {
      name: name.trim(),
      product_type: "credit",
      category,
      bank_name: bank.trim() || null,
      purpose: composePurpose(),
      currency,
      rate: Number.parseFloat(rate.value),
      term_months: term.value ? Number.parseInt(term.value, 10) : null,
      min_amount: minAmount.numericValue,
      max_amount: maxAmount.numericValue,
      initial_payment_pct: initialPayment.value ? Number.parseFloat(initialPayment.value) : null,
    };

    const validationError = validateProductForm(payload, t);
    if (validationError) {
      setFormError(validationError);
      return;
    }

    setSubmitting(true);
    try {
      const response = await apiFetch(isEdit ? `/api/products/${editId}` : "/api/products", {
        method: isEdit ? "PATCH" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        throw new Error((await readErrorDetail(response)) || `${response.status}`);
      }
      await applySaveResult(response, editId, t, goBackOr, open);
    } catch (err: any) {
      setFormError(saveErrorMessage(err, t));
    } finally {
      setSubmitting(false);
    }
  }

  const offersByBank = new Map<string, { index: number; offer: any }[]>();
  (existingOffers ?? []).forEach((offer, index) => {
    if (!offersByBank.has(offer.bankName)) offersByBank.set(offer.bankName, []);
    offersByBank.get(offer.bankName)!.push({ index, offer });
  });

  let copyFromPlaceholderLabel: string;
  if (existingOffersError) copyFromPlaceholderLabel = t("copy_from_error");
  else if (existingOffers === null) copyFromPlaceholderLabel = t("copy_from_loading");
  else copyFromPlaceholderLabel = t("copy_from_placeholder");

  if (loadingProduct) return <p className="empty-note">{t("bank_grid_loading")}</p>;
  if (loadError) return <p className="form-error">{t("edit_load_error")}</p>;

  return (
    <div className="pp-form-view">
      <section className="pp-hero form-hero">
        <h1>{t(isEdit ? "modal_title_edit" : "modal_title_new")}</h1>
        <p className="pp-form-subtitle">{t(isEdit ? "pp_edit_subtitle" : "pp_form_subtitle")}</p>
      </section>
      <form onSubmit={handleSubmit}>
        {/* Tahrirlashda bazadagi tarifdan nusxalash ma'noga ega emas — maydonlar
            allaqachon shu mahsulotning ma'lumotlari bilan to'ldirilgan. */}
        {!isEdit && (
          <div className="form-copy">
            <label htmlFor="npCopyFrom">{t("copy_from_label")}</label>
            <select
              id="npCopyFrom"
              value={copyFromIndex}
              onChange={e => handleCopyFromChange(e.target.value)}>
              <option value="">{copyFromPlaceholderLabel}</option>
              {[...offersByBank.entries()].map(([bankName, items], group) => (
                <optgroup label={bankName} key={`g${group}:${bankName}`}>
                  {items.map(({ index, offer }) => (
                    // `index` — ro'yxatdagi noyob tartib raqami: bir bankda nomi va
                    // stavkasi bir xil ikki tarif bo'lsa nom+foiz kaliti juldur
                    // bo'lib, React bu option'lardan birini yo'qotardi.
                    <option value={index} key={index}>
                      {offer.row.data.name ?? t("copy_from_unnamed")} — {offer.rate.percent}%
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
            {copySourceUrl && (
              <div className="form-copy-source">
                <SourceLink url={copySourceUrl} />
              </div>
            )}
          </div>
        )}

        <div className="pp-card">
          <h3>{t("pp_card_basic")}</h3>
          <div className="form-row">
            <label>
              <span>{t("field_name_label")}</span>
              <input
                type="text"
                required
                maxLength={200}
                placeholder={t("field_name_placeholder")}
                value={name}
                onChange={e => setName(e.target.value)}
              />
            </label>
            <label>
              <span>{t("field_category_label")}</span>
              <select
                required
                value={category}
                onChange={e => handleCategoryChange(e.target.value)}>
                {CATEGORY_OPTIONS.map(o => (
                  <option value={o.value} key={o.value}>
                    {t(o.key)}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {activeSubFields.length > 0 && (
            <div className="form-row">
              {activeSubFields.includes("carMarketType") && (
                <label>
                  <span>{t("field_car_market_type_label")}</span>
                  <select value={carMarketType} onChange={e => setCarMarketType(e.target.value)}>
                    <option value="">{t("field_car_market_type_placeholder")}</option>
                    <option value="Birlamchi bozor">{t("car_market_type_primary")}</option>
                    <option value="Ikkilamchi bozor">{t("car_market_type_secondary")}</option>
                  </select>
                </label>
              )}
              {activeSubFields.includes("carBrand") && (
                <label>
                  <span>{t("field_car_brand_label")}</span>
                  <select value={carBrand} onChange={e => setCarBrand(e.target.value)}>
                    <option value="">{t("field_car_brand_placeholder")}</option>
                    {CAR_BRANDS.map(brand => (
                      <option value={brand} key={brand}>
                        {brand}
                      </option>
                    ))}
                    <option value="Boshqa">{t("car_brand_other")}</option>
                  </select>
                </label>
              )}
              {activeSubFields.includes("mortgageType") && (
                <label>
                  <span>{t("field_mortgage_type_label")}</span>
                  <select value={mortgageType} onChange={e => setMortgageType(e.target.value)}>
                    <option value="">{t("field_mortgage_type_placeholder")}</option>
                    <option value="Birlamchi bozor">{t("mortgage_type_primary")}</option>
                    <option value="Ikkilamchi bozor">{t("mortgage_type_secondary")}</option>
                  </select>
                </label>
              )}
              {activeSubFields.includes("consumerType") && (
                <label>
                  <span>{t("field_consumer_type_label")}</span>
                  <select value={consumerType} onChange={e => setConsumerType(e.target.value)}>
                    <option value="">{t("field_consumer_type_placeholder")}</option>
                    <option value="Naqd pul krediti">{t("consumer_type_cash")}</option>
                    <option value="Tovar krediti">{t("consumer_type_goods")}</option>
                  </select>
                </label>
              )}
              {activeSubFields.includes("microType") && (
                <label>
                  <span>{t("field_micro_type_label")}</span>
                  <select value={microType} onChange={e => setMicroType(e.target.value)}>
                    <option value="">{t("field_micro_type_placeholder")}</option>
                    <option value="Tadbirkorlik uchun">{t("micro_type_business")}</option>
                    <option value="Iste'mol uchun">{t("micro_type_consumer")}</option>
                  </select>
                </label>
              )}
              {activeSubFields.includes("educationType") && (
                <label>
                  <span>{t("field_education_type_label")}</span>
                  <select value={educationType} onChange={e => setEducationType(e.target.value)}>
                    <option value="">{t("field_education_type_placeholder")}</option>
                    <option value="Mahalliy OTM">{t("education_type_local")}</option>
                    <option value="Xorijiy OTM">{t("education_type_foreign")}</option>
                  </select>
                </label>
              )}
            </div>
          )}

          <div className="form-row">
            <label>
              <span>{t("field_bank_label")}</span>
              <input
                type="text"
                maxLength={150}
                placeholder={t("field_bank_placeholder")}
                value={bank}
                onChange={e => setBank(e.target.value)}
              />
            </label>
            <label>
              <span>{t("field_purpose_label")}</span>
              <input
                type="text"
                maxLength={300}
                placeholder={t("field_purpose_placeholder")}
                value={purpose}
                onChange={e => setPurpose(e.target.value)}
              />
            </label>
          </div>
        </div>

        <div className="pp-card">
          <h3>{t("pp_card_financial")}</h3>
          <div className="form-row">
            <label>
              <span>{t("field_min_amount_label")}</span>
              <input
                type="text"
                inputMode="decimal"
                autoComplete="off"
                placeholder="1 000 000"
                ref={minAmount.inputRef}
                value={minAmount.displayValue}
                onChange={minAmount.onChange}
                onKeyDown={minAmount.onKeyDown}
              />
            </label>
            <label>
              <span>{t("field_max_amount_label")}</span>
              <input
                type="text"
                inputMode="decimal"
                autoComplete="off"
                placeholder="50 000 000"
                ref={maxAmount.inputRef}
                value={maxAmount.displayValue}
                onChange={maxAmount.onChange}
                onKeyDown={maxAmount.onKeyDown}
              />
            </label>
          </div>
          <div className="form-row">
            <label>
              <span>{t("field_currency_label")}</span>
              <select value={currency} onChange={e => setCurrency(e.target.value)}>
                <option value="UZS">UZS</option>
                <option value="USD">USD</option>
                <option value="EUR">EUR</option>
              </select>
            </label>
            <label>
              <span>{t("field_rate_label")}</span>
              <input
                type="number"
                step="0.01"
                min="0"
                max="100"
                required
                placeholder="20"
                value={rate.value}
                onChange={rate.onChange}
                onKeyDown={rate.onKeyDown}
              />
            </label>
          </div>
          <div className="form-row">
            <label>
              <span>{t("field_term_label")}</span>
              <input
                type="number"
                step="1"
                min="1"
                max="240"
                placeholder="24"
                value={term.value}
                onChange={term.onChange}
                onKeyDown={term.onKeyDown}
              />
            </label>
            <label>
              <span>{t("field_initial_payment_label")}</span>
              <input
                type="number"
                step="0.01"
                min="0"
                max="100"
                placeholder="30"
                value={initialPayment.value}
                onChange={initialPayment.onChange}
                onKeyDown={initialPayment.onKeyDown}
              />
            </label>
          </div>
        </div>

        {formError && <p className="form-error">{formError}</p>}
        <div className="pp-form-actions">
          <button type="button" className="btn-secondary" onClick={() => goBackOr("/products")}>
            {t("cancel_btn")}
          </button>
          <button type="submit" className="btn-primary" disabled={submitting}>
            {t(isEdit ? "update_btn" : "submit_btn")}
          </button>
        </div>
      </form>
    </div>
  );
}
