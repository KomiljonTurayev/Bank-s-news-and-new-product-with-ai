import { changeDirection } from "@/shared/lib/format";

export default function ChangeBadge({ changePct }: Readonly<{ changePct: number }>) {
  const { dir, arrow } = changeDirection(changePct);
  return (
    <span className={`mpl-change mpl-${dir}`}>
      {arrow} {Math.abs(changePct).toFixed(2)}%
    </span>
  );
}
