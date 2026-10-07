import {
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { hotStableContext } from "@/shared/lib/hot-context";
import { fetchJSON, registerSessionCache } from "@/shared/api/base";

const CurrencyContext = hotStableContext<any>("CurrencyContext", null);

// MPL (Min/O'rtacha/Max) davr-bo'yicha valyuta statistikasi keshi va
// eng oxirgi ko'rilgan davrning kod->o'zgarish(%) xaritasi — bank
// kartalaridagi valyuta bloklariga ham shu ma'lumot qo'shiladi, shunda
// foydalanuvchi qaysi bank taklifi qachon arzonlashgan/qimmatlashganini
// kartada ham ko'radi.
export function CurrencyProvider({ children }: Readonly<{ children: ReactNode }>) {
  const cacheRef = useRef(new Map<string, any>());
  const chartCacheRef = useRef(new Map<string, any>());
  const [changeByCode, setChangeByCode] = useState<Record<string, number>>({});

  // Sessiya almashganda bu keshlar ham tozalansin (Provider butun ilova
  // davomida mount bo'lib turadi — logout'da o'zi unmount bo'lmaydi).
  useEffect(
    () =>
      registerSessionCache(() => {
        cacheRef.current.clear();
        chartCacheRef.current.clear();
        setChangeByCode({});
      }),
    [],
  );

  const getCachedStats = useCallback((period: string) => cacheRef.current.get(period), []);

  const fetchStats = useCallback(async (period: string) => {
    if (cacheRef.current.has(period)) return cacheRef.current.get(period);
    const stats = await fetchJSON(`/api/rates/currency-stats?days=${encodeURIComponent(period)}`);
    cacheRef.current.set(period, stats);
    return stats;
  }, []);

  const applyChanges = useCallback((stats: any[]) => {
    setChangeByCode(Object.fromEntries(stats.map(s => [s.code, s.change_pct])));
  }, []);

  const getCachedHistory = useCallback(
    (code: string, period: string) => chartCacheRef.current.get(`${code}:${period}`),
    [],
  );

  const fetchHistory = useCallback(async (code: string, period: string) => {
    const key = `${code}:${period}`;
    if (chartCacheRef.current.has(key)) return chartCacheRef.current.get(key);
    const data = await fetchJSON(
      `/api/rates/currency-history?code=${encodeURIComponent(code)}&days=${encodeURIComponent(period)}`,
    );
    chartCacheRef.current.set(key, data);
    return data;
  }, []);

  // `value` har render'da yangi obyek bo'lmasligi uchun memoizatsiya qilinadi
  // (S6481) — aks holda Provider ostidagi hamma iste'molchi qayta render bo'ladi.
  const value = useMemo(
    () => ({
      changeByCode,
      getCachedStats,
      fetchStats,
      applyChanges,
      getCachedHistory,
      fetchHistory,
    }),
    [changeByCode, getCachedStats, fetchStats, applyChanges, getCachedHistory, fetchHistory],
  );
  return <CurrencyContext.Provider value={value}>{children}</CurrencyContext.Provider>;
}

export function useCurrency() {
  const ctx = useContext(CurrencyContext);
  if (!ctx) throw new Error("useCurrency must be used within CurrencyProvider");
  return ctx;
}
