import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { RevenuePoint } from "@/api/dashboard";
import { CHART_BASELINE, CHART_GRIDLINE, CHART_INK_MUTED, CHART_INK_SECONDARY, SEQUENTIAL_COLOR } from "@/lib/chartColors";
import { tooltipContentStyle, tooltipLabelStyle } from "./tooltipStyle";

const currency = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });

interface ChartRow {
  period: string;
  revenue: number | null;
  forecastRevenue: number | null;
}

interface Props {
  data: RevenuePoint[];
  forecast?: RevenuePoint[];
}

export default function RevenueLineChart({ data, forecast }: Props) {
  const chartData: ChartRow[] = data.map((d, i) => ({
    period: d.period,
    revenue: d.revenue,
    // the last actual point also seeds the forecast series so the dashed line
    // visually connects to where the solid line ends, instead of a gap.
    forecastRevenue: forecast && forecast.length > 0 && i === data.length - 1 ? d.revenue : null,
  }));
  if (forecast && forecast.length > 0) {
    chartData.push(...forecast.map((f) => ({ period: f.period, revenue: null, forecastRevenue: f.revenue })));
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={chartData} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
        <CartesianGrid stroke={CHART_GRIDLINE} vertical={false} />
        <XAxis
          dataKey="period"
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
          formatter={(value, name) => [currency.format(Number(value)), name]}
        />
        {forecast && forecast.length > 0 && (
          <Legend wrapperStyle={{ fontSize: 12, color: CHART_INK_SECONDARY }} />
        )}
        <Line
          type="monotone"
          dataKey="revenue"
          name="Actual"
          stroke={SEQUENTIAL_COLOR}
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
          isAnimationActive="auto"
          animationBegin={60}
          animationDuration={780}
          animationEasing="ease-out"
        />
        {forecast && forecast.length > 0 && (
          <Line
            type="monotone"
            dataKey="forecastRevenue"
            name="Forecast"
            stroke={SEQUENTIAL_COLOR}
            strokeWidth={2}
            strokeDasharray="5 5"
            strokeOpacity={0.6}
            dot={false}
            activeDot={{ r: 4 }}
            isAnimationActive="auto"
            animationBegin={120}
            animationDuration={620}
            animationEasing="ease-out"
          />
        )}
      </LineChart>
    </ResponsiveContainer>
  );
}
