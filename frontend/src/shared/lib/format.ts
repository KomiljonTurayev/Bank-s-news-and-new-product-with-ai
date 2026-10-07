// ═══════════════════════════════════════════════════════════════════
// UMUMIY FORMATLASH YORDAMCHI FUNKSIYALARI
// ═══════════════════════════════════════════════════════════════════
export function initials(name: string) {
  // `/\(.*\)/` qo'sh o'rnida: birinchi "(" dan oxirgi ")" gacha bo'lgan qismni
  // xuddi shu chegara bilan olamiz, lekin backtracking'siz, chiziqli (S8786) —
  // `.*` + ")" ketma-ketligi uzoq qavsli satrlarda polinomial vaqt sarflardi.
  const open = name.indexOf("(");
  const close = name.lastIndexOf(")");
  const withoutParen =
    open !== -1 && close > open ? name.slice(0, open) + name.slice(close + 1) : name;
  return withoutParen
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map(w => w[0])
    .join("")
    .toUpperCase();
}

export function formatTime(iso: string, locale?: string) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString(locale, {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function fmtRate(n: number, locale?: string) {
  return Number(n).toLocaleString(locale, { maximumFractionDigits: 2 });
}

export function fmtDate(iso: string) {
  const [y, m, d] = iso.split("-");
  return `${d}.${m}.${y}`;
}

export function fmtDateShort(iso: string) {
  const [, m, d] = iso.split("-");
  return `${d}.${m}`;
}

// Foiz o'zgarishi belgisi (yashil "▲"/qizil "▼"/"—") — MPL jadvali,
// valyuta widget'i va bank kartalaridagi valyuta bloki bir xil
// oshgan/tushgan/o'zgarmagan uch holatni bir xil rang-belgi bilan
// ko'rsatadi, shu bois bitta joyda hisoblanadi.
export function changeDirection(changePct: number) {
  if (changePct > 0) {
    return { dir: "up", arrow: "▲" };
  }
  if (changePct < 0) {
    return { dir: "down", arrow: "▼" };
  }
  return { dir: "", arrow: "—" };
}
