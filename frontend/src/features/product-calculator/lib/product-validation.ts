export const NP_TERM_MAX_MONTHS = 240; // 20 yil — eng uzun keng tarqalgan kredit muddati
import { NP_MAX_AMOUNT } from "./use-amount-field";

// Backend (app/api.py CustomProductIn) ham xuddi shu chegaralarni mustaqil
// tekshiradi — frontend faqat foydalanuvchiga tezroq va aniqroq xabar
// berish uchun.
// Summa maydonlarining chegaraviy tekshiruvlari. Xabarlar avvalgi bilan
// bir xil tartibda qaytariladi (bir nechta xato bo'lsa qaysi biri ko'rinadi).
function validateAmounts(payload: any, t: (key: string, vars?: any) => string) {
  if (payload.min_amount !== null && payload.min_amount < 0) return t("val_min_negative");
  if (payload.max_amount !== null && payload.max_amount < 0) return t("val_max_negative");
  if (payload.min_amount !== null && payload.min_amount > NP_MAX_AMOUNT)
    return t("val_min_too_big");
  if (payload.max_amount !== null && payload.max_amount > NP_MAX_AMOUNT)
    return t("val_max_too_big");
  if (
    payload.min_amount !== null &&
    payload.max_amount !== null &&
    payload.min_amount > payload.max_amount
  ) {
    return t("val_min_gt_max");
  }
  return null;
}

export function validateProductForm(payload: any, t: (key: string, vars?: any) => string) {
  if (!Number.isFinite(payload.rate)) return t("val_rate_required");
  if (payload.rate < 0 || payload.rate > 1000) return t("val_rate_range");
  if (
    payload.term_months !== null &&
    (!Number.isInteger(payload.term_months) ||
      payload.term_months < 1 ||
      payload.term_months > NP_TERM_MAX_MONTHS)
  ) {
    return t("val_term_range", { max: NP_TERM_MAX_MONTHS });
  }
  const amountsError = validateAmounts(payload, t);
  if (amountsError) return amountsError;
  if (
    payload.initial_payment_pct !== null &&
    (payload.initial_payment_pct < 0 || payload.initial_payment_pct > 100)
  ) {
    return t("val_initial_payment_range");
  }
  return null;
}
