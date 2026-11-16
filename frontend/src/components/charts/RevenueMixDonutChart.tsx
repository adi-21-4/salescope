import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { CATEGORICAL_COLORS, CHART_SURFACE } from "@/lib/chartColors";
import { tooltipContentStyle, tooltipLabelStyle } from "./tooltipStyle";
export interface DimensionShare {
  label: string;
  revenue: number;
  pct: number;
}

const currency = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0, notation: "compact", compactDisplay: "short" });
const fullCurrency = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });

interface Props {
  data: DimensionShare[];
  emptyMessage: string;
}

export default function RevenueMixDonutChart({ data, emptyMessage }: Props) {
  if (data.length === 0) return <p className="chart-empty-message">{emptyMessage}</p>;

  const total = data.reduce((sum, item) => sum + item.revenue, 0);
  const chartData = data.map((item) => ({ ...item, name: item.label }));

  return (
    <div className="revenue-mix-layout">
      <div className="donut-plot" role="img" aria-label={`${data.length} revenue shares totaling ${fullCurrency.format(total)}`}>
        <ResponsiveContainer width="100%" height={180}>
          <PieChart>
            <Tooltip contentStyle={{ ...tooltipContentStyle, backgroundColor: CHART_SURFACE, opacity: 1, boxShadow: "0 8px 24px rgba(25,50,45,.16)" }} wrapperStyle={{ zIndex: 30 }} labelStyle={tooltipLabelStyle} formatter={(value, name, item) => [`${fullCurrency.format(Number(value))} · ${item.payload.pct}%`, String(name)]} />
            <Pie data={chartData} dataKey="revenue" nameKey="name" innerRadius="62%" outerRadius="88%" paddingAngle={2} stroke={CHART_SURFACE} strokeWidth={2} isAnimationActive="auto" animationBegin={40} animationDuration={620} animationEasing="ease-out">
              {chartData.map((item, index) => <Cell key={item.label} fill={CATEGORICAL_COLORS[index % CATEGORICAL_COLORS.length]} />)}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <div className="donut-center" aria-hidden="true"><strong>{currency.format(total)}</strong><span>Total revenue</span></div>
      </div>
      <ul className="revenue-mix-legend" aria-label="Revenue share by group">
        {chartData.map((item, index) => <li key={item.label} title={`${item.label}: ${fullCurrency.format(item.revenue)} (${item.pct}%)`}>
          <i style={{ backgroundColor: CATEGORICAL_COLORS[index % CATEGORICAL_COLORS.length] }} />
          <span>{item.label}</span><span className="revenue-mix-values"><b>{item.pct}%</b><small>{currency.format(item.revenue)}</small></span>
        </li>)}
      </ul>
    </div>
  );
}
