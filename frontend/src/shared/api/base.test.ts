import { beforeEach, describe, expect, it, vi } from "vitest";

import { fetchJSON, invalidateJsonCache, registerSessionCache, resetSessionCaches } from "./base";

function jsonResponse(body: unknown, status = 200): Response {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as Response;
}

beforeEach(() => {
  localStorage.clear();
  resetSessionCaches();
  vi.unstubAllGlobals();
});

describe("fetchJSON keshi", () => {
  it("ikkinchi so'rovni keshdan beradi va har chaqiruvga alohida nusxa qaytaradi", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ v: 1 }));
    vi.stubGlobal("fetch", fetchMock);

    const a = await fetchJSON("/api/x");
    const b = await fetchJSON("/api/x");

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(a).toEqual({ v: 1 });
    expect(b).toEqual({ v: 1 });
    expect(b).not.toBe(a);
  });

  it("bir vaqtdagi bir xil so'rovlar bitta g'ildirakka birlashadi", async () => {
    let resolveFirst!: (res: Response) => void;
    const fetchMock = vi
      .fn()
      .mockImplementation(() => new Promise<Response>(res => (resolveFirst = res)));
    vi.stubGlobal("fetch", fetchMock);

    const p1 = fetchJSON("/api/y");
    const p2 = fetchJSON("/api/y");
    resolveFirst(jsonResponse({ v: 2 }));

    expect(await p1).toEqual({ v: 2 });
    expect(await p2).toEqual({ v: 2 });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("xato keshlanmaydi — keyingi chaqiruv so'rovni qayta uradi va status saqlanadi", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({}, 503))
      .mockResolvedValueOnce(jsonResponse({ v: 3 }));
    vi.stubGlobal("fetch", fetchMock);

    const err = await fetchJSON("/api/z").catch(e => e as Error & { status?: number });
    expect(err).toBeInstanceOf(Error);
    expect(err.status).toBe(503);

    await expect(fetchJSON("/api/z")).resolves.toEqual({ v: 3 });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("invalidateJsonCache(merchant) faqat mos kalitlarni o'chiradi", async () => {
    const fetchMock = vi.fn(async (url: string) => jsonResponse({ url }));
    vi.stubGlobal("fetch", fetchMock);

    await fetchJSON("/api/products/1");
    await fetchJSON("/api/meta");
    expect(fetchMock).toHaveBeenCalledTimes(2);

    invalidateJsonCache("/api/products");
    await fetchJSON("/api/products/1");
    await fetchJSON("/api/meta");
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });
});

describe("sessiya keshlari", () => {
  it("resetSessionCaches o'z keshini tozalaydi va ro'yxatdagi keshlarni chaqiradi", async () => {
    const fetchMock = vi.fn(async (url: string) => jsonResponse({ url, n: 1 }));
    vi.stubGlobal("fetch", fetchMock);
    const clearSpy = vi.fn();
    const unregister = registerSessionCache(clearSpy);

    await fetchJSON("/api/x");
    resetSessionCaches();
    expect(clearSpy).toHaveBeenCalledTimes(1);

    await fetchJSON("/api/x");
    expect(fetchMock).toHaveBeenCalledTimes(2);

    unregister();
    resetSessionCaches();
    expect(clearSpy).toHaveBeenCalledTimes(1);
  });

  it("sessiya almashganda yolib bo'lmagan eski javob yangi keshga yozilmaydi", async () => {
    let resolveStale!: (res: Response) => void;
    const fetchMock = vi
      .fn()
      .mockImplementationOnce(() => new Promise<Response>(res => (resolveStale = res)))
      .mockResolvedValueOnce(jsonResponse({ session: "new" }));
    vi.stubGlobal("fetch", fetchMock);

    const stale = fetchJSON("/api/meta");
    resetSessionCaches(); // so'rov ketayotib sessiya almashdi
    resolveStale(jsonResponse({ session: "old" }));
    await stale;

    // Eski javob keshga tushmagan bo'lishi kerak — yangi sessiya qayta so'raydi.
    await expect(fetchJSON("/api/meta")).resolves.toEqual({ session: "new" });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
