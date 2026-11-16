import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ProductRevenue } from "@/api/dashboard";
import { CHART_GRIDLINE, CHART_INK_MUTED, SEQUENTIAL_COLOR } from "@/lib/chartColors";
import { tooltipContentStyle, tooltipLabelStyle } from "./tooltipStyle";

const currency = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });

interface Props {
  data: ProductRevenue[];
  emptyMessage?: string;
}

export default function ProductsBarChart({ data, emptyMessage }: Props) {
  if (data.length === 0) {
    return (
      <p className="text-sm text-[hsl(var(--muted-foreground))]">
        {emptyMessage ?? "No data."}
      </p>
    );
  }
  const height = Math.max(120, data.length * 32);
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 24, left: 8, bottom: 4 }}>
        <CartesianGrid stroke={CHART_GRIDLINE} horizontal={false} />
        <XAxis
          type="number"
          tick={{ fill: CHART_INK_MUTED, fontSize: 12 }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => currency.format(v)}
        />
        <YAxis
          type="category"
          dataKey="product"
          tick={{ fill: CHART_INK_MUTED, fontSize: 12 }}
          axisLine={false}
          tickLine={false}
          width={110}
        />
        <Tooltip
          contentStyle={tooltipContentStyle}
          labelStyle={tooltipLabelStyle}
          formatter={(value) => [currency.format(Number(value)), "Revenue"]}
        />
        <Bar dataKey="revenue" fill={SEQUENTIAL_COLOR} radius={[0, 4, 4, 0]} barSize={16} isAnimationActive="auto" animationBegin={50} animationDuration={650} animationEasing="ease-out" />
      </BarChart>
    </ResponsiveContainer>
  );
}
