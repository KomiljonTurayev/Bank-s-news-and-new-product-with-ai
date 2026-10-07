import type { ReactNode } from "react";

import { useI18n } from "@/shared/lib/i18n/i18n-context";
import { useOffers } from "@/entities/offer";

import Tabs from "./tabs";
import FilterBar from "./filter-bar";
import TopOffers from "./top-offers";
import Toolbar from "./toolbar";
import ComparePanel from "./compare-panel";
import OfferCards from "./offer-cards";
import OfferTable from "./offer-table";
import OfferChart from "./offer-chart";

export default function OffersSection() {
  const { t } = useI18n();
  const { view, loading, error, stale } = useOffers();

  let content: ReactNode;
  if (loading) {
    content = (
      <section className="bank-grid">
        <div className="loading">{t("bank_grid_loading")}</div>
      </section>
    );
  } else if (error) {
    content = (
      <section className="bank-grid">
        <div className="loading">{t("load_data_error")}</div>
      </section>
    );
  } else if (view === "table") {
    content = <OfferTable />;
  } else if (view === "chart") {
    content = <OfferChart />;
  } else {
    content = <OfferCards />;
  }

  return (
    <>
      <Tabs />
      <FilterBar />
      <TopOffers />
      <Toolbar />
      <ComparePanel />
      {stale && <div className="source-stale-note">{t("load_data_stale")}</div>}
      {content}
    </>
  );
}
