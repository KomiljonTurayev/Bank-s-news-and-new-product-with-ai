// ═══════════════════════════════════════════════════════════════════
// TAKLIFLAR YOZUVLARI USTIDA ISHLASH: foiz/muddat ajratib olish,
// saralash va bank katalogi qurish
// ═══════════════════════════════════════════════════════════════════

// Bir yozuvdan foiz stavkasini topadi (masalan "22%" yoki "14%") — mahsulot
// turlari orasida maydon nomlari har xil bo'lgani uchun (Foiz/rate) generik
// qidiradi. Avval nomida "foiz"/"stavka" so'zi bor maydonni qidiramiz.
export function extractRate(
  data: Record<string, any>,
  { t, locale }: { t: (key: string) => string; locale?: string },
) {
  const buildResult = (key: string, value: string) => {
    const match = /-?\d+(?:[.,]\d+)?/.exec(value);
    if (!match) return null;
    const label = `${match[0]}%`;
    const hideFromDetails = value.trim().length <= label.length + 6;
    return { key, label, percent: Number.parseFloat(match[0].replace(",", ".")), hideFromDetails };
  };

  for (const [key, value] of Object.entries(data)) {
    if (typeof value === "string" && value.includes("%") && /foiz|stavka/i.test(key)) {
      const result = buildResult(key, value);
      if (result) return result;
    }
  }
  for (const [key, value] of Object.entries(data)) {
    if (typeof value === "string" && value.includes("%")) {
      const result = buildResult(key, value);
      if (result) return result;
    }
  }
  // Valyuta kursi kabi foizsiz, lekin sonli "rate" maydoniga ega mahsulotlar
  // ham saralash/solishtirish uchun shu yagona yo'l orqali o'tishi kerak.
  if (typeof data.rate === "number") {
    return {
      key: "rate",
      label: `${data.rate.toLocaleString(locale)} ${t("sum_currency")}`,
      percent: data.rate,
      hideFromDetails: true,
    };
  }
  return { key: null, label: "—", percent: null, hideFromDetails: true };
}

// Kredit turidagi mahsulotlar uchun PASTROQ foiz mijozga foydali, boshqa
// barcha turlar (omonat, investitsiya, valyuta, kredit karta) uchun esa
// YUQORIROQ foiz foydali — "Eng maqbul" saralash shuni hisobga oladi.
function isBetterWhenLower(row: any) {
  return row.product_type === "credit" || row.data.category === "Kredit karta";
}

export function sortScore(
  row: any,
  mode: string,
  ctx: { t: (key: string) => string; locale?: string },
) {
  const percent = extractRate(row.data, ctx).percent;
  if (percent === null) return null;
  if (mode !== "best") return percent;
  return isBetterWhenLower(row) ? -percent : percent;
}

// `(\d+)\s*oy` naqshi raqam bilan bo'shliq chegarasida kvadratik qaytish
// qiladi, shuning uchun avval to'liq raqam bolag'i olinib, undan keyingi
// qator tekshiriladi — natija bir xil, skan chiziqli.
function numberFollowedBy(value: string, suffix: RegExp): number | null {
  for (const run of value.matchAll(/\d+/g)) {
    if (suffix.test(value.slice((run.index ?? 0) + run[0].length))) {
      return Number.parseInt(run[0], 10);
    }
  }
  return null;
}

const AFTER_MONTH_RE = /^\s*oy/i;
const AFTER_YEAR_RE = /^\s*yil/i;

// Bir yozuvdan muddatni (oyda) topadi — faqat nomida "muddat" so'zi bor
// maydonlarni qidiradi.
export function extractTermMonths(data: Record<string, any>) {
  for (const [key, value] of Object.entries(data)) {
    if (typeof value !== "string" || !/muddat/i.test(key)) continue;
    const months = numberFollowedBy(value, AFTER_MONTH_RE);
    if (months !== null) return months;
    const years = numberFollowedBy(value, AFTER_YEAR_RE);
    if (years !== null) return years * 12;
  }
  return null;
}

export function buildBankDirectory(rows: any[], banks: { code: string; name: string }[]) {
  const map = new Map(banks.map(b => [b.code, b.name]));
  for (const row of rows) {
    if (!map.has(row.bank_code)) {
      map.set(row.bank_code, row.data.bank_name || row.bank_code);
    }
  }
  return map;
}

// React ro'yxat kaliti. Bir mahsulot bir nechta manbadan keladi (masalan
// depozit.uz agregatori va bankning rasmiy sayti), valyutada esa bir kod
// ikki tomonga (sotib olish/sotish) ega — faqat nom bo'yicha kalit
// takrorlanadi, shu bois manba, havola va tomon ham kalitga kiradi.
export function recordKey(row: any): string {
  const d = row.data ?? {};
  return `${row.bank_code ?? ""}|${d.source ?? ""}|${d.url ?? ""}|${d.code ?? d.name ?? ""}|${d.side ?? ""}|${d.date ?? ""}|${d.rate ?? ""}`;
}

export function groupByBank(rows: any[]) {
  const map = new Map<string, any[]>();
  for (const row of rows) {
    if (!map.has(row.bank_code)) map.set(row.bank_code, []);
    map.get(row.bank_code)!.push(row);
  }
  return map;
}
