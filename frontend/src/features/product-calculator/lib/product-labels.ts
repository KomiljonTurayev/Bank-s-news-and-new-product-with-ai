const PRODUCT_TYPE_LABEL_KEYS: Record<string, string> = {
  deposit: "product_type_deposit",
  credit: "product_type_credit",
  card: "product_type_card",
  investment: "product_type_investment",
};
export function productTypeLabel(type: string, t: (key: string) => string) {
  return PRODUCT_TYPE_LABEL_KEYS[type] ? t(PRODUCT_TYPE_LABEL_KEYS[type]) : type;
}

// "category" backendda doim shu 6 ta o'zbekcha qiymatdan biri sifatida
// saqlanadi (npCategory select'idagi <option value> bilan bir xil).
const CATEGORY_LABEL_KEYS: Record<string, string> = {
  "Iste'mol krediti": "cat_consumer",
  Ipoteka: "cat_mortgage",
  Avtokredit: "cat_auto",
  "Ta'lim krediti": "cat_education",
  Overdraft: "cat_overdraft",
  Mikroqarz: "cat_micro",
};
export function categoryLabel(category: string, t: (key: string) => string) {
  return CATEGORY_LABEL_KEYS[category] ? t(CATEGORY_LABEL_KEYS[category]) : category;
}

export function scoreRankText(score: number, t: (key: string) => string) {
  if (score >= 75) return t("rank_very_competitive");
  if (score >= 50) return t("rank_above_average");
  if (score >= 25) return t("rank_below_average");
  return t("rank_weak_competitive");
}
