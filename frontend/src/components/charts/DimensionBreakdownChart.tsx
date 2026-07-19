import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { CATEGORICAL_COLORS } from "@/lib/chartColors";
import { tooltipContentStyle, tooltipLabelStyle } from "./tooltipStyle";

const currency = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });

export interface DimensionShare {
  label: string;
  revenue: number;
  pct: number;
}

interface Props {
  data: DimensionShare[];
  emptyMessage: string;
}

export default function DimensionBreakdownChart({ data, emptyMessage }: Props) {
  if (data.length === 0) {
    return <p className="text-sm text-[hsl(var(--muted-foreground))]">{emptyMessage}</p>;
  }

  // Reshape into a single stacked row: {row: "Revenue", [label]: revenue, ...}
  const row: Record<string, string | number> = { row: "Revenue" };
  for (const d of data) row[d.label] = d.revenue;

  return (
    <div>
      <ResponsiveContainer width="100%" height={70}>
        <BarChart data={[row]} layout="vertical" margin={{ top: 4, right: 12, left: 0, bottom: 4 }}>
          <XAxis type="number" hide />
          <YAxis type="category" dataKey="row" hide />
          <Tooltip
            contentStyle={tooltipContentStyle}
            labelStyle={tooltipLabelStyle}
            formatter={(value, name) => [currency.format(Number(value)), String(name)]}
          />
          {data.map((d, i) => (
            <Bar
              key={d.label}
              dataKey={d.label}
              stackId="a"
              fill={CATEGORICAL_COLORS[i % CATEGORICAL_COLORS.length]}
              radius={i === 0 ? [4, 0, 0, 4] : i === data.length - 1 ? [0, 4, 4, 0] : undefined}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
      <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-2 text-sm">
        {data.map((d, i) => (
          <li key={d.label} className="flex items-center gap-2">
            <span
              className="h-2.5 w-2.5 rounded-full"
              style={{ background: CATEGORICAL_COLORS[i % CATEGORICAL_COLORS.length] }}
            />
            <span>
              {d.label} — {d.pct}% ({currency.format(d.revenue)})
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
