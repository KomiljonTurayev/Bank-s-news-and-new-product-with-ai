import { useI18n } from "@/shared/lib/i18n/i18n-context";
import { recordKey, useOffers, useRateFormat } from "@/entities/offer";
import { matchesFilters } from "@/shared/lib/matches-filters";
import { initials } from "@/shared/lib/format";

import ProductBlock from "./product-block";

// recordKey maydonlari bir xil, lekin muddati farq qiluvchi ikki lif
// uchraydi — kartalar darajasida tartib raqami bilan yakuniy noyoblik.
export default function OfferCards() {
  const { t, tn } = useI18n();
  const { directory, byBank, product, sort, search, compareSet } = useOffers();
  const { sortScore } = useRateFormat();

  let visibleBanks = Array.from(directory, ([code, name]) => ({ code, name })).filter((b: any) =>
    matchesFilters(b.code, b.name, { search, compareSet }),
  );

  if (product === "currency") {
    // Valyuta kursi bankka bog'liq bo'lmagan yagona (CBU) manbadan keladi —
    // ma'lumoti bo'lmagan banklarni bo'sh karta sifatida ko'rsatish shart emas.
    visibleBanks = visibleBanks.filter((b: any) => byBank.has(b.code));
  }

  if (!visibleBanks.length) {
    return (
      <section className="bank-grid">
        <div className="loading">{t("bank_grid_not_found")}</div>
      </section>
    );
  }

  const withData = visibleBanks.filter((b: any) => byBank.has(b.code));
  const withoutData = visibleBanks.filter((b: any) => !byBank.has(b.code));

  const bankSortValue = (records: any[]) => {
    const vals = records.map(r => sortScore(r, sort)).filter(v => v !== null);
    if (!vals.length) return null;
    return sort === "rate_asc" ? Math.min(...vals) : Math.max(...vals);
  };

  withData.sort((a: any, b: any) => {
    if (sort === "bank_az") return a.name.localeCompare(b.name);
    const va = bankSortValue(byBank.get(a.code));
    const vb = bankSortValue(byBank.get(b.code));
    if (sort === "rate_asc") {
      if (va === null && vb === null) return 0;
      if (va === null) return 1;
      if (vb === null) return -1;
      return va - vb;
    }
    return (vb ?? -Infinity) - (va ?? -Infinity);
  });

  const ordered =
    sort === "bank_az"
      ? visibleBanks.slice().sort((a: any, b: any) => a.name.localeCompare(b.name))
      : [...withData, ...withoutData];

  return (
    <section className="bank-grid">
      {ordered.map((bank: any) => {
        const records = (byBank.get(bank.code) ?? []).slice().sort((a: any, b: any) => {
          const sa = sortScore(a, sort);
          const sb = sortScore(b, sort);
          if (sort === "rate_asc") return (sa ?? Infinity) - (sb ?? Infinity);
          return (sb ?? -Infinity) - (sa ?? -Infinity);
        });

        let body;
        if (!records.length) {
          body = <p className="empty-note">{t("bank_no_data")}</p>;
        } else if (product === "currency") {
          // Valyuta tabida "Yana N ta" ortida yashirmaymiz — bank taklif
          // qilgan barcha valyutalarni kartada to'liq ko'rsatamiz.
          body = records.map((r: any, i: number) => (
            <ProductBlock record={r} key={`${recordKey(r)}#${i}`} />
          ));
        } else {
          const visible = records.slice(0, 2);
          const rest = records.slice(2);
          body = (
            <>
              {visible.map((r: any, i: number) => (
                <ProductBlock record={r} key={`${recordKey(r)}#${i}`} />
              ))}
              {rest.length > 0 && (
                <details className="more-products">
                  <summary>{tn("more_offers", rest.length)}</summary>
                  {rest.map((r: any, i: number) => (
                    <ProductBlock record={r} key={`${recordKey(r)}#${i + records.length}`} />
                  ))}
                </details>
              )}
            </>
          );
        }

        return (
          <article className={`bank-card${records.length ? "" : " empty"}`} key={bank.code}>
            <div className="bank-card-header">
              <div className="bank-logo">{initials(bank.name)}</div>
              <h3>{bank.name}</h3>
              {records.length > 0 && (
                <span className="bank-count">{tn("offer_count", records.length)}</span>
              )}
            </div>
            {body}
          </article>
        );
      })}
    </section>
  );
}
