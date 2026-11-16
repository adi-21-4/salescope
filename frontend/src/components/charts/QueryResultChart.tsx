import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { NLDataPoint } from "@/api/query";
import { CHART_BASELINE, CHART_GRIDLINE, CHART_INK_MUTED, SEQUENTIAL_COLOR } from "@/lib/chartColors";
import { tooltipContentStyle, tooltipLabelStyle } from "./tooltipStyle";

const currency = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });

interface Props {
  data: NLDataPoint[];
  chartType: "line" | "bar" | "number";
}

export default function QueryResultChart({ data, chartType }: Props) {
  if (data.length === 0) return null;

  if (chartType === "number") {
    return <p className="text-3xl font-semibold tabular-nums">{currency.format(data[0].value)}</p>;
  }

  const ChartComponent = chartType === "line" ? LineChart : BarChart;
  const height = Math.max(180, Math.min(400, data.length * 36));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <ChartComponent data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
        <CartesianGrid stroke={CHART_GRIDLINE} vertical={false} />
        <XAxis
          dataKey="label"
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
          formatter={(value) => [currency.format(Number(value)), "Value"]}
        />
        {chartType === "line" ? (
          <Line type="monotone" dataKey="value" stroke={SEQUENTIAL_COLOR} strokeWidth={2} dot={false} isAnimationActive="auto" animationBegin={60} animationDuration={700} animationEasing="ease-out" />
        ) : (
          <Bar dataKey="value" fill={SEQUENTIAL_COLOR} radius={[4, 4, 0, 0]} isAnimationActive="auto" animationBegin={60} animationDuration={620} animationEasing="ease-out" />
        )}
      </ChartComponent>
    </ResponsiveContainer>
  );
}
