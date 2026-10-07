import { useContext, useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import { hotStableContext } from "@/shared/lib/hot-context";

import {
  I18N,
  SUPPORTED_LANGS,
  DEFAULT_LANG,
  CURRENCY_NAMES_I18N,
  CURRENCY_NAMES_RU_GENITIVE,
  FIELD_KEY_LABELS,
  FIELD_VALUE_LABELS,
} from "./dictionary";

const LOCALE_MAP: Record<string, string> = { uz: "uz-UZ", ru: "ru-RU" };

function interpolate(template: string, vars: Record<string, any>) {
  return template.replace(/\{(\w+)\}/g, (match, key) => (key in vars ? String(vars[key]) : match));
}

// Rus tilida sonlarga qarab uchta shakl bor (1 — one, 2-4 — few, 5+ — many);
// o'zbek tilida otlar songa qarab turlanmaydi, shu bois barcha shakl bir xil bo'ladi.
function pluralCategory(lang: string, n: number) {
  const abs = Math.abs(n);
  if (lang === "ru") {
    const mod10 = abs % 10;
    const mod100 = abs % 100;
    if (mod10 === 1 && mod100 !== 11) return "one";
    if (mod10 >= 2 && mod10 <= 4 && !(mod100 >= 12 && mod100 <= 14)) return "few";
    return "many";
  }
  return "many";
}

function normalizeFieldToken(s: any) {
  // `/[*•]+$/` o'rniga chiziqli sikl: anchor oldidan `+` qatorning har
  // pozitsiyasidan qayta-sarflab, polinomial vaqtga ketardi (S8786).
  const text = String(s).trim();
  let end = text.length;
  while (end > 0 && (text[end - 1] === "*" || text[end - 1] === "•")) end--;
  return text.slice(0, end).trim().toLowerCase();
}

// Ko'p bank saytlari o'z manzilining BIRINCHI yo'l segmentida til kodini
// ko'rsatadi. Havola aynan shu andozaga mos kelsa, joriy interfeys tiliga
// moslab almashtiramiz — aks holda hech narsa o'zgartirilmaydi.
const URL_LANG_SEGMENT_RE = /^([a-z][a-z0-9+.-]*:\/\/[^/]+\/)(uz|ru)(\/.*)?$/i;

// depozit.uz — standart (prefikssiz) URL o'zbekcha, rus tili uchun "/ru"
// segmenti QO'SHILADI (mavjud "/uz/" bilan ALMASHTIRILMAYDI).
const DEPOZIT_UZ_HOST_RE = /^(https?:\/\/(?:www\.)?depozit\.uz)(\/.*)?$/i;
function localizeDepozitUz(url: string, lang: string) {
  const m = DEPOZIT_UZ_HOST_RE.exec(url);
  if (!m) return null;
  const [, origin, rest] = m;
  const restWithoutLang = (rest || "").replace(/^\/(uz|ru)(?=\/|\?|#|$)/i, "");
  const prefix = lang === "ru" ? "/ru" : "";
  return `${origin}${prefix}${restWithoutLang}`;
}

function localizeExternalUrl(url: any, lang: string) {
  if (typeof url !== "string") return url;
  const depozit = localizeDepozitUz(url, lang);
  if (depozit !== null) return depozit;
  const match = URL_LANG_SEGMENT_RE.exec(url);
  if (!match) return url;
  const [, prefix, , rest] = match;
  return `${prefix}${lang}${rest ?? ""}`;
}

function initialLang() {
  const saved = localStorage.getItem("lang");
  if (saved && SUPPORTED_LANGS.includes(saved)) return saved;
  const browserLang = (navigator.language || "").slice(0, 2).toLowerCase();
  return SUPPORTED_LANGS.includes(browserLang) ? browserLang : DEFAULT_LANG;
}

const I18nContext = hotStableContext<any>("I18nContext", null);

export function I18nProvider({ children }: Readonly<{ children: ReactNode }>) {
  const [lang, setLang] = useState(initialLang);

  const persistLang = useCallback((next: string) => {
    if (!SUPPORTED_LANGS.includes(next)) return;
    localStorage.setItem("lang", next);
    setLang(next);
  }, []);

  const value = useMemo(() => {
    const t = (key: string, vars?: Record<string, any>) => {
      const template = I18N[lang]?.[key] ?? I18N[DEFAULT_LANG][key] ?? key;
      return vars ? interpolate(template, vars) : template;
    };

    // "Rich" tarjima: lug'at shablonidagi `<b>…</b>` teglari JSX `<b>`
    // elementlariga aylantiriladi. Teglar shablondan OLDIN ajratiladi,
    // o'zgaruvchilar har bir matn bo'lagiga alohida interpolyatsiya qilinadi
    // — shuning uchun qiymatlar (masalan API'dan kelgan valyuta kodi) HTML
    // bo'lib emmas, JSX matni sifatida ekranlanadi. dangerouslySetInnerHTML
    // o'rnini shu usul bosadi (SEC-APP-03 kanali shu yerda yopiladi).
    const tRich = (key: string, vars?: Record<string, any>): ReactNode[] => {
      const template = I18N[lang]?.[key] ?? I18N[DEFAULT_LANG][key] ?? key;
      const seen = new Map<string, number>();
      return String(template)
        .split(/<b>([\s\S]*?)<\/b>/g)
        .map((part, i) => {
          const text = interpolate(part, vars ?? {});
          const bold = i % 2 === 1;
          // Kluch bo'lak matnidan: ro'yxat har bir renderda shu shablondan
          // qayta tiklanadi, indeks esa izdosh bo'lak siljlsa o'zgaradi.
          const base = (bold ? "b:" : "t:") + text;
          const n = (seen.get(base) ?? 0) + 1;
          seen.set(base, n);
          return bold ? <b key={`${base}#${n}`}>{text}</b> : text;
        });
    };

    const tn = (key: string, count: number, vars?: Record<string, any>) => {
      const entry = I18N[lang]?.[key] ?? I18N[DEFAULT_LANG][key];
      const category = pluralCategory(lang, count);
      const template = (typeof entry === "object" ? (entry[category] ?? entry.many) : entry) ?? key;
      return interpolate(template, { ...vars, count });
    };

    const currencyName = (code: string) =>
      CURRENCY_NAMES_I18N[code]?.[lang] ?? CURRENCY_NAMES_I18N[code]?.[DEFAULT_LANG] ?? code;

    // "{name} kursi" / "курс {name}" kabi valyuta nomi GAP ICHIDA
    // ishlatiladigan joylar uchun — faqat rus tilida nominativdan farq qiladi.
    const currencyNameInPhrase = (code: string) =>
      lang === "ru" ? (CURRENCY_NAMES_RU_GENITIVE[code] ?? currencyName(code)) : currencyName(code);

    const translateFieldKey = (key: string) => {
      const norm = normalizeFieldToken(key);
      return FIELD_KEY_LABELS[lang]?.[norm] ?? key;
    };

    const translateFieldValue = (value: any) => {
      if (lang === "uz" || typeof value !== "string") return value;
      const norm = normalizeFieldToken(value);
      return FIELD_VALUE_LABELS[lang]?.[norm] ?? value;
    };

    const locale = LOCALE_MAP[lang] || LOCALE_MAP.uz;
    const safeUrl = (url: any) => {
      if (typeof url !== "string") return null;
      if (!/^https?:\/\//i.test(url)) return null;
      return localizeExternalUrl(url, lang);
    };

    return {
      lang,
      setLang: persistLang,
      t,
      tRich,
      tn,
      currencyName,
      currencyNameInPhrase,
      translateFieldKey,
      translateFieldValue,
      locale,
      safeUrl,
    };
  }, [lang, persistLang]);

  useEffect(() => {
    document.documentElement.lang = lang;
    document.title = value.t("page_title");
  }, [lang, value]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used within I18nProvider");
  return ctx;
}
