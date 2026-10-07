import { useI18n } from "@/shared/lib/i18n/i18n-context";

import Truncatable from "./truncatable";

const OTHER_FIELDS_MAX_LEN = 90;
const OTHER_FIELD_LONG_ENTRY_LEN = 40;

// "Qo'shimcha" ustuni ba'zi banklarda juda uzun bo'lib, jadval/kartani
// buzib yuborishi mumkin edi — shu bois qisqartirib, kerak bo'lsa to'liq
// matnni ko'rsatish uchun almashtiriladigan qiladi. Bir nechta qisqa
// maydon yig'indisi 90 belgidan oshib ketishi mumkin — "ko'proq" faqat
// haqiqatan uzun (bitta) qiymat bo'lganda chiqishi uchun, hech bir
// maydon uzun bo'lmasa qisqartirmaymiz.
export default function OtherFields({
  data,
  skipKeys,
  fallback = null,
}: Readonly<{
  data: Record<string, any>;
  skipKeys: Set<string>;
  fallback?: any;
}>) {
  const { translateFieldKey, translateFieldValue } = useI18n();
  const entries = Object.entries(data)
    .filter(([key]) => !skipKeys.has(key))
    .map(([key, value]) => `${translateFieldKey(key)}: ${translateFieldValue(value)}`);
  if (!entries.length) return fallback;

  const full = entries.join(" • ");
  const hasLongEntry = entries.some(entry => entry.length > OTHER_FIELD_LONG_ENTRY_LEN);
  if (!hasLongEntry || full.length <= OTHER_FIELDS_MAX_LEN) return <>{full}</>;

  return <Truncatable text={full} maxLen={OTHER_FIELDS_MAX_LEN} />;
}
