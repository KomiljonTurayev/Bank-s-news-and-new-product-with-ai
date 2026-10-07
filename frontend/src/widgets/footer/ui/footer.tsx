import { useI18n } from "@/shared/lib/i18n/i18n-context";

export default function Footer() {
  const { t } = useI18n();
  return (
    <footer className="site-footer">
      <p>{t("footer_text")}</p>
    </footer>
  );
}
