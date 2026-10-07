// ═══════════════════════════════════════════════════════════════════
// MPL "katta diagramma" uchun geometriya hisob-kitoblari (chizishning
// o'zi komponentda JSX/SVG sifatida amalga oshiriladi)
// ═══════════════════════════════════════════════════════════════════
const CHART_W = 760;
const CHART_H = 240;
const PAD_L = 54;
const PAD_R = 14;
const PAD_T = 16;
const PAD_B = 26;

// Heckbert "nice numbers": o'q bo'yicha chiroyli (qatrov, 2/5 ga karrali)
// bosqichlar — 12,653.25 kabi chiroqlikni buzuvchi qiymatlar chiqmasin.
function niceNum(range: number, round: boolean) {
  const exp = Math.floor(Math.log10(range));
  const f = range / 10 ** exp;
  let nf: number;
  if (round) {
    if (f < 1.5) nf = 1;
    else if (f < 3) nf = 2;
    else if (f < 7) nf = 5;
    else nf = 10;
  } else if (f <= 1) nf = 1;
  else if (f <= 2) nf = 2;
  else if (f <= 5) nf = 5;
  else nf = 10;
  return nf * 10 ** exp;
}

export function buildChartGeometry(
  points: { date: string; value: number }[],
  width = CHART_W,
  height = CHART_H,
) {
  const w = Math.max(width, 240);
  const h = Math.max(height, 160);
  const innerW = w - PAD_L - PAD_R;
  const innerH = h - PAD_T - PAD_B;
  const values = points.map(p => p.value);
  const rawMin = Math.min(...values);
  const rawMax = Math.max(...values);
  const rawRange = rawMax - rawMin || Math.max(Math.abs(rawMax) * 0.01, 1);
  const yStep = niceNum(rawRange / 4, true);
  const min = Math.floor(rawMin / yStep) * yStep;
  const max = Math.ceil(rawMax / yStep) * yStep;
  const range = max - min;
  const stepX = points.length > 1 ? innerW / (points.length - 1) : 0;
  const toY = (v: number) => PAD_T + innerH - ((v - min) / range) * innerH;
  const xy = points.map((p, i) => ({
    x: PAD_L + i * stepX,
    y: toY(p.value),
    date: p.date,
    value: p.value,
  }));

  const yTicks: { value: number; y: number }[] = [];
  for (let v = max, i = 0; i <= 9 && v >= min - yStep * 1e-6; v -= yStep, i++) {
    yTicks.push({ value: v, y: toY(v) });
  }

  const xTickCount = Math.max(
    1,
    Math.min(Math.round(innerW / 150), 8, Math.max(points.length - 1, 1)),
  );
  const xTicks = Array.from({ length: xTickCount + 1 }, (_, i) => {
    const idx = Math.round(((points.length - 1) * i) / xTickCount);
    let anchor: string;
    if (i === 0) anchor = "start";
    else if (i === xTickCount) anchor = "end";
    else anchor = "middle";
    return { x: xy[idx].x, date: points[idx].date, anchor };
  });

  return { xy, w, h, padL: PAD_L, padT: PAD_T, innerW, innerH, stepX, yTicks, xTicks };
}

export function statsFromPoints(points: { date: string; value: number }[]) {
  const values = points.map(p => p.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const avg = values.reduce((a, b) => a + b, 0) / values.length;
  const current = points.at(-1)!.value;
  const first = points.at(0)!.value;
  const change_pct = first ? ((current - first) / first) * 100 : 0;
  return { min, max, avg, current, change_pct };
}
