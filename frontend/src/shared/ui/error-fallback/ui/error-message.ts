// Xato obyektyidan foydalanuvchiga ko'rsatiladigan xabar satrini oladi.
// `String(err)` oddiy obyektni "[object Object]" qilib yuboradi (S6551) —
// shu bois faqat aniq shakllar qaytariladi, qolgani yumshoq fallback.
export function errorMessage(error: unknown): string {
  // Error — oldagi `error instanceof Error ? error.message : ...` bilan bayt-ba-bayt
  // bir xil: `message` o'zgarmasdan qaytadi (bo'sh satr ham bo'lsa).
  if (error instanceof Error) return error.message;
  if (typeof error === "string") return error;
  if (error === null || error === undefined) return "Unknown error";
  // Bu tarmoqda `error` TIPI endi primer (number/boolean/bigint), shu bois
  // `String(...)` aniq va S6551 ni qo'zg'atmaydi.
  if (typeof error === "number" || typeof error === "boolean" || typeof error === "bigint") {
    return String(error);
  }
  // Oddiy obyekt / funksiya / symbol: oldin "[object Object]" bo'lib chiqardi.
  return "Unknown error";
}
