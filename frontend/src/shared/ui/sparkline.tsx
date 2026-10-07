// Kurs grafigi uchun minigrafik. viewBox qafasi CSS qutisidan kengroq/tor
// bo'lishi mumkin (preserveAspectRatio="none"), shu bois chiziq qalinligi
// vector-effect bilan, oxirgi nuqta esa SVG ichida emas, HTML qatlamda
// ko'rsatiladi — aks holda nuqta cho'zilib ellips bo'lib qoladi.
export default function Sparkline({ values }: Readonly<{ values?: number[] }>) {
  if (!values || values.length < 2) return null;
  const w = 100;
  const h = 28;
  const pad = 3;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const step = (w - pad * 2) / (values.length - 1);
  const xy = values.map(
    (v, i) => [pad + i * step, h - pad - ((v - min) / range) * (h - pad * 2)] as const,
  );
  const points = xy.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const up = values.at(-1)! >= values.at(0)!;
  const [lastX, lastY] = xy.at(-1)!;
  const color = up ? "var(--pos)" : "var(--accent)";

  return (
    <span
      className={`spark-wrap ${up ? "spark-up" : "spark-down"}`}
      style={
        {
          ["--dot-x" as string]: `${(lastX / w) * 100}%`,
          ["--dot-y" as string]: `${(lastY / h) * 100}%`,
        } as React.CSSProperties
      }>
      <svg
        className="sparkline"
        viewBox={`0 0 ${w} ${h}`}
        preserveAspectRatio="none"
        aria-hidden="true">
        <polygon
          className="spark-area"
          points={`${pad},${h} ${points} ${w - pad},${h}`}
          fill={color}
        />
        <polyline
          points={points}
          fill="none"
          stroke={color}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          vectorEffect="non-scaling-stroke"
        />
      </svg>
      <span className="spark-dot" aria-hidden="true" />
    </span>
  );
}
