import { useI18n } from "@/shared/lib/i18n/i18n-context";

import { extractRate as extractRateBase, sortScore as sortScoreBase } from "./offers-data";

export function useRateFormat() {
  const { t, locale } = useI18n();
  const ctx = { t, locale };
  return {
    extractRate: (data: Record<string, any>) => extractRateBase(data, ctx),
    sortScore: (row: any, mode: string) => sortScoreBase(row, mode, ctx),
  };
}
