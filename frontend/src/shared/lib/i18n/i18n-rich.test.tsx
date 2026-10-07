import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { I18nProvider, useI18n } from "./i18n-context";

function RichProbe() {
  const { tRich } = useI18n();
  return (
    <p data-testid="rich">
      {tRich("mpl_chart_sentence", {
        period: "30 kun",
        name: "<img src=x onerror=alert(1)>",
        min: "100",
        max: "<script>alert(2)</script>",
        current: "105",
        dir: "oshdi",
        changePct: "5%",
      })}
    </p>
  );
}

describe("tRich (SEC-APP-03 kanali yopilishi)", () => {
  it("lug'atdagi <b> teglari haqiqiy JSX elementlariga aylanadi", () => {
    render(
      <I18nProvider>
        <RichProbe />
      </I18nProvider>,
    );
    const out = screen.getByTestId("rich");
    expect(out.querySelectorAll("b")).toHaveLength(3);
  });

  it("o'zgaruvchi qiymatlari HTML emas, matn sifatida ekranlanadi (XSS)", () => {
    render(
      <I18nProvider>
        <RichProbe />
      </I18nProvider>,
    );
    const out = screen.getByTestId("rich");
    expect(out.querySelector("img")).toBeNull();
    expect(out.querySelector("script")).toBeNull();
    // Qiymat hizb-hizbi matn bo'lib ko'rinadi — DOM'ga teg bo'lib sizib kirmaydi.
    expect(out.textContent).toContain("<img src=x onerror=alert(1)>");
  });
});
