import { useI18n } from "@/shared/lib/i18n/i18n-context";
import { useOffers } from "@/entities/offer";

export default function ComparePanel() {
  const { t } = useI18n();
  const { byBank, directory, compareSet, toggleCompare, clearCompare } = useOffers();

  const codes = Array.from(byBank.keys() as IterableIterator<string>).sort((a, b) =>
    (directory.get(a) || a).localeCompare(directory.get(b) || b),
  );

  return (
    <div className="compare-panel">
      <div className="compare-panel-head">
        <span>{t("compare_panel_head")}</span>
        {compareSet.size > 0 && (
          <button className="compare-clear" onClick={clearCompare}>
            {t("compare_clear")}
          </button>
        )}
      </div>
      <div className="compare-chips">
        {codes.length === 0 ? (
          <span className="empty-note">{t("compare_empty")}</span>
        ) : (
          codes.map(code => (
            <button
              key={code}
              className={`compare-chip${compareSet.has(code) ? " active" : ""}`}
              onClick={() => toggleCompare(code)}>
              {directory.get(code) ?? code}
            </button>
          ))
        )}
      </div>
    </div>
  );
}
