import { useEffect, useState } from "react";

import { MplScreen } from "@/widgets/mpl-screen";

export default function Mpl() {
  const [openChartCode, setOpenChartCode] = useState<string | null>(null);

  // Escape ochilgan katta diagrammani yopadi.
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setOpenChartCode(null);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  return <MplScreen openChartCode={openChartCode} setOpenChartCode={setOpenChartCode} />;
}
