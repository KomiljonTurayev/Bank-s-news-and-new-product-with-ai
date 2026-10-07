import { useMemo } from "react";
import { useDispatch, useSelector } from "react-redux";

// FSD: quyqi slice app qatlamidan faqat TIPLARNI oladi (import type kompilyatsiyada o'chadi).
import type { AppDispatch, RootState } from "@/app/store";
import { useMeta } from "@/entities/meta";

import { buildBankDirectory, groupByBank } from "../lib/offers-data";
import {
  setProduct,
  setSearch,
  setSort,
  setView,
  toggleCompare,
  clearCompare,
} from "./offers-ui-slice";
import { useOffersQuery } from "./use-offers-query";

// Segment UI'dan olib tashlandi (Jismoniy/Yuridik tanlagichi yo'q), lekin
// backend so'rovi segment parametriga moyil — katalog doim jismoniy
// shaxslar takliflarini ko'rsatadi.
const SEGMENT = "individual";

// Eski Context-based useOffers() bilan BIR XIL qaytish shaklini beradi —
// UI holati (redux) + server ma'lumoti (react-query) + hosila
// (directory/byBank/latestFetch) shu yerda birlashtiriladi, shunda
// ko'plab iste'molchi komponentlarni deyarli o'zgartirmasdan ko'chirish
// mumkin bo'ldi.
export function useOffers() {
  const dispatch = useDispatch<AppDispatch>();
  const { banks, loaded: metaLoaded } = useMeta();
  const ui = useSelector((s: RootState) => s.offersUi);

  const { data, isLoading, isError } = useOffersQuery(ui.product, SEGMENT);
  const rows = data ?? [];

  const directory = useMemo(() => buildBankDirectory(rows, banks), [rows, banks]);
  const byBank = useMemo(() => groupByBank(rows), [rows]);
  const latestFetch = useMemo(
    () => rows.reduce((max: string, r: any) => (r.fetched_at > max ? r.fetched_at : max), ""),
    [rows],
  );
  const compareSet = useMemo(() => new Set(ui.compareCodes), [ui.compareCodes]);

  return {
    product: ui.product,
    setProduct: (v: string) => dispatch(setProduct(v)),
    search: ui.search,
    setSearch: (v: string) => dispatch(setSearch(v)),
    sort: ui.sort,
    setSort: (v: string) => dispatch(setSort(v)),
    view: ui.view,
    setView: (v: string) => dispatch(setView(v)),
    compareSet,
    toggleCompare: (code: string) => dispatch(toggleCompare(code)),
    clearCompare: () => dispatch(clearCompare()),
    rows,
    directory,
    byBank,
    // Banklar ro'yxati (/api/meta) va tariflar so'rovi PARALEL boshlanadi —
    // agar faqat tariflar tayyorligini kutsak, hali kelmagan bank nomlari
    // (directory) bilan chala ro'yxat bir lahzaga ko'rinib qolishi mumkin
    // edi. Ikkalasi ham tayyor bo'lgunicha "loading" davom etadi.
    loading: isLoading || !metaLoaded,
    // Biror manba yiqilganda ko'rib turgan ma'lumot yo'qolmasligi kerak.
    // React-query oxirgi muvaffaqiyatli javobni saqlab qoladi, shu bois
    // xatolik faqat ko'rsatadigan yozuv UMUMAN bo'lmaganda butun bo'limni
    // almashtiradi; aks holda eski (lekin haqiqiy) ma'lumot ostida
    // ogohlantirish ko'rsatiladi — `stale`.
    // Oddiy `rows.length` yetarli emas: oxirgi muvaffaqiyatli javob EMPTY
    // bo'lsa (bankaning o'sha kuni bo'sh katalogi), yiqilgan refetch bo'limni
    // butunlay almashtirib yubormasligi kerak — `data` aniqlanganligi
    // "qo'lda haqiqiy javob bor" deganidir.
    error: isError && data === undefined,
    stale: isError && data !== undefined,
    latestFetch,
  };
}
