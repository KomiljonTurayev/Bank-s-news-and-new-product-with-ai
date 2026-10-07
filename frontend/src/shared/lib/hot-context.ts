import { createContext, type Context } from "react";

/**
 * Vite HMR'da modul qayta bajarilganda `createContext` yana chaqirilsa, yangi
 * kontekst obyekti hosul bo'ladi: React daraxtidagi provider eski nusxani
 * ushlab qoladi, o'sha paytda yangilanigan konsumentlar esa yangisini o'qiydi
 * va "useI18n must be used within I18nProvider" xatosi ko'tariladi. Kontekstni
 * HMR holatiga saqlab, bir dona obyekt saqlanadi.
 */
export const hotStableContext = <T>(key: string, defaultValue: T): Context<T> => {
  const hot = import.meta.hot;
  // `hot.data` faqat dev-server HMR'da mavjud (vitest stub'ida yo'q).
  if (!hot?.data) return createContext<T>(defaultValue);
  if (!hot.data[key]) hot.data[key] = createContext<T>(defaultValue);
  return hot.data[key] as Context<T>;
};
