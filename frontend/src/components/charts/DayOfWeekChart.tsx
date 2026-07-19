import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { DayOfWeekPoint } from "@/api/dashboard";
import { CHART_BASELINE, CHART_GRIDLINE, CHART_INK_MUTED, SEQUENTIAL_COLOR } from "@/lib/chartColors";
import { tooltipContentStyle, tooltipLabelStyle } from "./tooltipStyle";

const currency = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });
const SHORT_DAY: Record<string, string> = {
  Monday: "Mon",
  Tuesday: "Tue",
  Wednesday: "Wed",
  Thursday: "Thu",
  Friday: "Fri",
  Saturday: "Sat",
  Sunday: "Sun",
};

export default function DayOfWeekChart({ data }: { data: DayOfWeekPoint[] }) {
  const chartData = data.map((d) => ({ ...d, shortDay: SHORT_DAY[d.day] ?? d.day }));
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={chartData} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
        <CartesianGrid stroke={CHART_GRIDLINE} vertical={false} />
        <XAxis
          dataKey="shortDay"
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
          formatter={(value) => [currency.format(Number(value)), "Avg. revenue"]}
          labelFormatter={(_label, payload) => payload[0]?.payload.day ?? ""}
        />
        <Bar dataKey="avg_revenue" fill={SEQUENTIAL_COLOR} radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
