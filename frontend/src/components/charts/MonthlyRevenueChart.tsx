import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { RevenuePoint } from "@/api/dashboard";
import { CHART_BASELINE, CHART_GRIDLINE, CHART_INK_MUTED, SEQUENTIAL_COLOR } from "@/lib/chartColors";
import { tooltipContentStyle, tooltipLabelStyle } from "./tooltipStyle";

const currency = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });

export default function SeasonalChart({ data }: { data: RevenuePoint[] }) {
  const chartData = data.map((d) => {
    const date = new Date(`${d.period}T00:00:00`);
    return { ...d, shortMonth: new Intl.DateTimeFormat("en-IN", { month: "short", year: "2-digit" }).format(date) };
  });
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={chartData} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
        <CartesianGrid stroke={CHART_GRIDLINE} vertical={false} />
        <XAxis
          dataKey="shortMonth"
          tick={{ fill: CHART_INK_MUTED, fontSize: 12 }}
          axisLine={{ stroke: CHART_BASELINE }}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: CHART_INK_MUTED, fontSize: 12 }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => currency.format(v)}
          width={70}
        />
        <Tooltip
          contentStyle={tooltipContentStyle}
          labelStyle={tooltipLabelStyle}
          formatter={(value) => [currency.format(Number(value)), "Revenue"]}
        />
        <Bar dataKey="revenue" fill={SEQUENTIAL_COLOR} radius={[4, 4, 0, 0]} isAnimationActive="auto" animationBegin={120} animationDuration={520} animationEasing="ease-out" />
      </BarChart>
    </ResponsiveContainer>
  );
}
