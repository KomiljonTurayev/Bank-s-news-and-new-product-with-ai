import { render, screen } from "@testing-library/react";
import { useQuery } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { fetchJSON, resetSessionCaches } from "@/shared/api/base";

import { QueryProvider } from "./with-query";

const queryFn = vi.fn(() => fetchJSON("/api/offers"));

function Probe() {
  const { data } = useQuery({
    queryKey: ["offers"],
    queryFn,
    // Keshlangan qiymat "manguda" bo'lsin: qayta mount tufayli emas,
    // faqat sessiya tozalanishi tufayli qayta so'rov ketishini tekshiramiz.
    staleTime: Infinity,
    refetchOnWindowFocus: false,
  });
  return <div data-testid="out">{data ? `v=${data.v}` : "loading"}</div>;
}

beforeEach(() => {
  queryFn.mockClear();
  resetSessionCaches();
  vi.unstubAllGlobals();
});

describe("react-query keshi sessiya almashuviga bo'ysunadi", () => {
  it("qayta mount keshdan beradi, resetSessionCaches'dan keyin esa qayta so'raydi", async () => {
    let n = 0;
    const fetchMock = vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => ({ v: ++n }),
    }));
    vi.stubGlobal("fetch", fetchMock);

    const first = render(
      <QueryProvider>
        <Probe />
      </QueryProvider>,
    );
    expect(await screen.findByText("v=1")).toBeDefined();
    expect(fetchMock).toHaveBeenCalledTimes(1);

    // Sessiya almashmagan — qayta mount mavjud keshdan o'qiydi, tarmoq yo'q.
    first.unmount();
    render(
      <QueryProvider>
        <Probe />
      </QueryProvider>,
    );
    expect(await screen.findByText("v=1")).toBeDefined();
    expect(fetchMock).toHaveBeenCalledTimes(1);

    // Sessiya almashdi — react-query keshi ham tozalanishi shart.
    resetSessionCaches();
    render(
      <QueryProvider>
        <Probe />
      </QueryProvider>,
    );
    expect(await screen.findByText("v=2")).toBeDefined();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
