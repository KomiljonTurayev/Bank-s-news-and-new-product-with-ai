import { useOffers, useRateFormat } from "@/entities/offer";

const MEDALS = ["1", "2", "3"];
// Kreditda bundan past stavka deyarli doim subsidiyali/aksiya ("0% dan",
// "foizsiz ipoteka") — "eng arzon" deb ko'rsatish chalg'itadi
// (backend: product_analysis._MIN_CREDIT_RATE bilan bir xil qoida).
const MIN_CREDIT_RATE = 10;

export default function TopOffers() {
  const { rows, directory, product } = useOffers();
  const { extractRate, sortScore } = useRateFormat();

  if (product === "currency" || !rows.length) return null;

  const withRate = rows
    .map((r: any) => ({ row: r, rate: extractRate(r.data), score: sortScore(r, "best") }))
    .filter((x: any) => x.score !== null)
    .filter((x: any) => product !== "credit" || (x.rate.percent ?? 0) >= MIN_CREDIT_RATE)
    .sort((a: any, b: any) => b.score - a.score)
    .slice(0, 3);

  if (!withRate.length) return null;

  return (
    <section className="top-offers">
      {withRate.map(({ row, rate }: any, i: number) => (
        <div
          className="top-offer-card"
          key={`${row.bank_code}-${row.data.name ?? row.data.code ?? ""}-${row.data.url ?? ""}#${i}`}>
          <span className="top-offer-rank">{MEDALS[i]}</span>
          <div>
            <div className="top-offer-bank">{directory.get(row.bank_code) ?? row.bank_code}</div>
            <div className="top-offer-name">{row.data.name ?? ""}</div>
          </div>
          <div className="top-offer-rate">{rate.label}</div>
        </div>
      ))}
    </section>
  );
}
