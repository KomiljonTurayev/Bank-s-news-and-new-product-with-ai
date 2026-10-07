import { useState } from "react";

import { useI18n } from "@/shared/lib/i18n/i18n-context";

// Instagramdagi "...ko'proq" uslubida: matnni berilgan uzunlikkacha
// (so'z chegarasidan) qisqartirib, "ko'proq" bosilganda shu joyning
// o'zida to'liq matnga almashadi.
export default function Truncatable({ text, maxLen }: Readonly<{ text: string; maxLen: number }>) {
  const { t } = useI18n();
  const [expanded, setExpanded] = useState(false);

  if (text.length <= maxLen) return <>{text}</>;

  let short = text.slice(0, maxLen);
  const lastSpace = short.lastIndexOf(" ");
  if (lastSpace > maxLen * 0.6) short = short.slice(0, lastSpace);

  return (
    <span className={`truncate${expanded ? " expanded" : ""}`}>
      <span className="truncate-text">{expanded ? text : `${short}…`}</span>{" "}
      <button type="button" className="truncate-toggle" onClick={() => setExpanded(e => !e)}>
        {expanded ? t("truncate_less") : t("truncate_more")}
      </button>
    </span>
  );
}
