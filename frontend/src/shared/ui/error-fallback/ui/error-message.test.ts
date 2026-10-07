import { describe, expect, it } from "vitest";

import { errorMessage } from "./error-message";

// Sonar S6551 dan oldingi ifoda — ko'rsatiladigan matn shu bilan
// Error(lar)da bayt-ba-bayt bir xil bo'lishi shart (kontrakt).
const legacy = (error: unknown) =>
  error instanceof Error ? error.message : String(error ?? "Unknown error");

describe("errorMessage", () => {
  it("Error misolida eski xatti-harakatni saqlaydi", () => {
    const cases: unknown[] = [
      new Error("Boom happened"),
      new TypeError("bad type"),
      new Error(""),
      new AggregateError([], ""),
      Error("plain"),
    ];
    for (const error of cases) expect(errorMessage(error)).toBe(legacy(error));
  });

  it("nomlar / qatorlar / null uchun ham ustma-ust tushadi", () => {
    for (const error of ["boom", "", 0, 42, true, false, 7n, null, undefined]) {
      expect(errorMessage(error)).toBe(legacy(error));
    }
  });

  it("obyektni '[object Object]' qilib yubormaydi", () => {
    expect(errorMessage({ code: 500 })).toBe("Unknown error");
    expect(errorMessage({ toString: () => "custom" })).toBe("Unknown error");
  });
});
