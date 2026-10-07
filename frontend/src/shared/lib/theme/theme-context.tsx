import { useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { hotStableContext } from "@/shared/lib/hot-context";

const ThemeContext = hotStableContext<any>("ThemeContext", null);

const SYSTEM_DEFAULT = "__system__";

function readStored(): string {
  try {
    return localStorage.getItem("theme") || SYSTEM_DEFAULT;
  } catch {
    return SYSTEM_DEFAULT;
  }
}

function systemTheme(): string {
  if (typeof window !== "undefined" && window.matchMedia) {
    return matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  return "light";
}

function resolve(stored: string): string {
  return stored === "dark" || stored === "light" ? stored : systemTheme();
}

export function ThemeProvider({ children }: Readonly<{ children: ReactNode }>) {
  const [theme, setTheme] = useState<string>(() => resolve(readStored()));

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  // Tanlov ochiq qilinmagunicha tizim rejimi jonli kuzatiladi
  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;
    const mq = matchMedia("(prefers-color-scheme: dark)");
    const onChange = (e: MediaQueryListEvent) => {
      if (readStored() === SYSTEM_DEFAULT) setTheme(e.matches ? "dark" : "light");
    };
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  // Boshqa oynada rejim almashtirilsa, shu oyna ham ortda qolmasin
  // (storage hodisasi qo'shni oynalarga keladi).
  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key !== "theme") return;
      setTheme(resolve(e.newValue || SYSTEM_DEFAULT));
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  // Faqat tugma bosilganda saqlanadi — saqlangan rejim tizimni eshitmaydi
  const toggleTheme = useCallback(() => {
    setTheme((current: string) => {
      const next = current === "dark" ? "light" : "dark";
      try {
        localStorage.setItem("theme", next);
      } catch {
        /* localStorage yopiq — rejim baribir ishlayveradi */
      }
      return next;
    });
  }, []);

  // `value` object identifikatori faqat `theme` o'zgarsa yangilanadi (S6481).
  const value = useMemo(() => ({ theme, toggleTheme }), [theme, toggleTheme]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within ThemeProvider");
  return ctx;
}
