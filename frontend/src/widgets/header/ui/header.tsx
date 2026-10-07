import { useEffect, useRef } from "react";
import { useDispatch } from "react-redux";

import { useI18n } from "@/shared/lib/i18n/i18n-context";
import { useTheme } from "@/shared/lib/theme/theme-context";
import { useOpenScreen } from "@/shared/lib/nav/use-open-screen";
import { resetOffersUi } from "@/entities/offer";

export default function Header() {
  const { t, lang, setLang } = useI18n();
  const { theme, toggleTheme } = useTheme();
  const dispatch = useDispatch();
  const { open, goHome } = useOpenScreen();

  // Ekranlar app bar ostidan boshlanadi — bar balandligi tornavon va
  // o'ramlarga qarab o'zgaradi, shu bois o'lchanib CSS o'zgaruvchisiga
  // yoziladi.
  const barRef = useRef<HTMLElement>(null);
  useEffect(() => {
    const bar = barRef.current;
    if (!bar) return;
    const publish = () =>
      document.documentElement.style.setProperty("--appbar-h", `${bar.offsetHeight}px`);
    publish();
    const observer = new ResizeObserver(publish);
    observer.observe(bar);
    return () => observer.disconnect();
  }, []);

  const onBrand = () => {
    dispatch(resetOffersUi());
    goHome();
  };

  return (
    <header className="topbar" ref={barRef}>
      <div className="topbar-inner">
        <button type="button" className="brand" onClick={onBrand} title={t("brand_home_title")}>
          <span className="brand-mark">B</span>
          <span className="brand-name">
            Bank's <b>News</b>
          </span>
        </button>

        <nav className="header-nav">
          <button type="button" className="header-nav-btn" onClick={() => open("/mpl")}>
            {t("header_nav_mpl")}
          </button>
          <button type="button" className="header-nav-btn" onClick={() => open("/products")}>
            {t("header_nav_product")}
          </button>
        </nav>

        <div className="lang-toggle" title={t("lang_toggle_title")}>
          <button
            className={`lang-btn${lang === "uz" ? " active" : ""}`}
            onClick={() => setLang("uz")}>
            UZ
          </button>
          <button
            className={`lang-btn${lang === "ru" ? " active" : ""}`}
            onClick={() => setLang("ru")}>
            RU
          </button>
        </div>

        <button className="theme-toggle" title={t("theme_toggle_title")} onClick={toggleTheme}>
          {theme === "dark" ? (
            <svg
              viewBox="0 0 24 24"
              width="17"
              height="17"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              aria-hidden="true">
              <circle cx="12" cy="12" r="4.2" />
              <path d="M12 2.5v2.4M12 19.1v2.4M2.5 12h2.4M19.1 12h2.4M5.3 5.3l1.7 1.7M17 17l1.7 1.7M18.7 5.3L17 7M7 17l-1.7 1.7" />
            </svg>
          ) : (
            <svg
              viewBox="0 0 24 24"
              width="17"
              height="17"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true">
              <path d="M20.5 13.3A8.5 8.5 0 1 1 10.7 3.5a6.8 6.8 0 0 0 9.8 9.8Z" />
            </svg>
          )}
        </button>
      </div>
    </header>
  );
}
