import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { I18nProvider, useI18n } from "./i18n-context";

function Probe() {
  const { safeUrl, translateFieldValue } = useI18n();
  return (
    <>
      <span data-testid="u1">{String(safeUrl("https://bank.uz/uz/products/?x=1"))}</span>
      <span data-testid="u2">{String(safeUrl("https://www.depozit.uz/uz/rates"))}</span>
      <span data-testid="u3">{String(safeUrl("https://bank.uz/ru/"))}</span>
      <span data-testid="u4">{String(safeUrl("javascript:alert(1)"))}</span>
      <span data-testid="u5">{String(safeUrl("https://bank.uz"))}</span>
      <span data-testid="n0">{String(translateFieldValue(42))}</span>
      <span data-testid="n1">{String(translateFieldValue("Debet Karta*"))}</span>
      <span data-testid="n2">{String(translateFieldValue("  debet karta •*  "))}</span>
      <span data-testid="n3">{String(translateFieldValue("DEBET KARTA"))}</span>
    </>
  );
}

const renderAt = (lang: string) => {
  localStorage.setItem("lang", lang);
  render(
    <I18nProvider>
      <Probe />
    </I18nProvider>,
  );
};

// `/[*•]+$/` regex'ining chiziqli siklga almashtirilishi (S8786) va
// `String.prototype.match` → `RegExp.prototype.exec` (S6594) qayta yozuvlari
// eski xatti-harakatni saqlashini tekshiruvchi himoya testlari.
describe("i18n URL va maydon normalizatsiyasi", () => {
  it("til segmenti hamda depozit.uz manzili tilga moslashadi", () => {
    renderAt("ru");
    expect(screen.getByTestId("u1").textContent).toBe("https://bank.uz/ru/products/?x=1");
    expect(screen.getByTestId("u2").textContent).toBe("https://www.depozit.uz/ru/rates");
    expect(screen.getByTestId("u3").textContent).toBe("https://bank.uz/ru/");
    expect(screen.getByTestId("u4").textContent).toBe("null");
    expect(screen.getByTestId("u5").textContent).toBe("https://bank.uz");
  });

  it("trailing markerlar (*) qirqilishi tarjimani o'zgartirmaydi", () => {
    renderAt("ru");
    const base = screen.getByTestId("n3").textContent;
    expect(screen.getByTestId("n1").textContent).toBe(base);
    expect(screen.getByTestId("n2").textContent).toBe(base);
  });

  it("satr bo'lmagan qiymat o'zgarmasdan qaytadi", () => {
    renderAt("ru");
    expect(screen.getByTestId("n0").textContent).toBe("42");
  });
});
