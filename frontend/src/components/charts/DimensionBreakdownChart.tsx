import type { CSSProperties } from "react";
import { CATEGORICAL_COLORS } from "@/lib/chartColors";
import type { DimensionShare } from "./RevenueMixDonutChart";

const currency = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });

interface Props {
  data: DimensionShare[];
  emptyMessage: string;
}

export default function DimensionBreakdownChart({ data, emptyMessage }: Props) {
  if (data.length === 0) return <p className="chart-empty-message">{emptyMessage}</p>;

  const sorted = [...data].sort((a, b) => b.revenue - a.revenue).slice(0, 8);
  return (
    <ul className="dimension-breakdown" aria-label="Revenue share by group">
      {sorted.map((item, index) => <li key={item.label} aria-label={`${item.label}: ${item.pct}% of revenue, ${currency.format(item.revenue)}`}>
        <div className="dimension-breakdown-heading"><span>{item.label}</span><strong>{item.pct}%</strong></div>
        <div className="dimension-breakdown-track" aria-hidden="true"><i style={{ backgroundColor: CATEGORICAL_COLORS[index % CATEGORICAL_COLORS.length], "--share": Math.max(0.025, Math.min(item.pct, 100) / 100), animationDelay: `${index * 32}ms` } as CSSProperties & { "--share": number }} /></div>
        <small>{currency.format(item.revenue)}</small>
      </li>)}
    </ul>
  );
}
