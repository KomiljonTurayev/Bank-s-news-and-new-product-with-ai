import { useI18n } from "@/shared/lib/i18n/i18n-context";

export default function Hero() {
  const { t } = useI18n();
  return (
    <section className="hero">
      <h1>{t("hero_title")}</h1>
      <p>{t("hero_subtitle")}</p>
    </section>
  );
}
