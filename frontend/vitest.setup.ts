import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// jsdom window'ida structuredClone bo'lmasa (Node'ningglobalini ham
// topilmasa) JSON-nusxa bilan qoplamalaymiz — base.ts keshi shunga tayanadi.
if (typeof globalThis.structuredClone !== "function") {
  globalThis.structuredClone = (v: unknown) => JSON.parse(JSON.stringify(v)) as never;
}

afterEach(cleanup);
