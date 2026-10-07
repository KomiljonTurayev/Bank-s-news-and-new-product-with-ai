import { useI18n } from "@/shared/lib/i18n/i18n-context";

// Ba'zi manbalar (depozit.uz, cbu.uz) bank kartasi ma'lumotini agregator
// sifatida beradi — havola aslida bankning o'z rasmiy saytiga emas, shu
// agregatorga olib boradi. "Bank saytida ko'rish" deb yolg'on va'da
// bermaslik uchun havola matni haqiqiy manzilga qarab tanlanadi.
export default function SourceLink({ url }: Readonly<{ url?: string }>) {
  const { t, safeUrl } = useI18n();
  const safe = safeUrl(url);
  if (!safe) return null;

  let host = "";
  try {
    host = new URL(safe).hostname.replace(/^www\./, "");
  } catch {
    host = "";
  }
  let label;
  if (!host) label = t("sourcelink_bank_site");
  else if (host === "cbu.uz") label = t("sourcelink_official_source", { host: "cbu.uz" });
  else if (host === "depozit.uz") label = t("sourcelink_source", { host: "depozit.uz" });
  else label = t("sourcelink_official_site", { host });

  return (
    <a className="product-link" href={safe} target="_blank" rel="noopener noreferrer">
      {label}
    </a>
  );
}
