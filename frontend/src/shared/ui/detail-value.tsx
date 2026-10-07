import { useI18n } from "@/shared/lib/i18n/i18n-context";

import Truncatable from "./truncatable";

const DETAIL_VALUE_MAX_LEN = 60;

// Bank kartalari ro'yxatidagi har bir maydon qiymati ham ba'zan juda uzun
// bo'lib chiqadi — xuddi "Qo'shimcha" ustunidagi kabi qisqartirib,
// "ko'proq" bilan to'liq matnga almashtiriladigan qiladi.
export default function DetailValue({ value }: Readonly<{ value: any }>) {
  const { translateFieldValue } = useI18n();
  const text = String(translateFieldValue(value));
  if (text.length <= DETAIL_VALUE_MAX_LEN) return <>{text}</>;
  return <Truncatable text={text} maxLen={DETAIL_VALUE_MAX_LEN} />;
}
