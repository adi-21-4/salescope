import { Link } from "react-router-dom";
import { ArrowUpRight, Users } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { AgentPerformance } from "@/api/dashboard";
import { CHART_GRIDLINE, CHART_INK_MUTED, SEQUENTIAL_COLOR } from "@/lib/chartColors";
import { tooltipContentStyle, tooltipLabelStyle } from "./tooltipStyle";

const currency = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });
const TIER_COLORS = { A: "#2F6B8A", B: "#B58A31", C: "#65728B" };

interface Props {
  data: AgentPerformance[];
  onSelectAgent?: (agent: AgentPerformance) => void;
}

export default function AgentPerformanceChart({ data, onSelectAgent }: Props) {
  if (data.length === 0) {
    return <div className="agent-empty"><span><Users size={17} /></span><p>No agent column is mapped for this dataset.</p><Link to="/upload">Import or map agent sales data <ArrowUpRight size={13} /></Link></div>;
  }

  const chartData = data.slice(0, 12);
  const chartHeight = Math.max(190, chartData.length * 31);
  return (
    <div className="agent-performance-layout">
      <div className="agent-chart" role="img" aria-label={`Revenue ranked across ${chartData.length} sales agents; bar colors identify Pareto tiers`}>
        <ResponsiveContainer width="100%" height={chartHeight}>
          <BarChart data={chartData} layout="vertical" margin={{ top: 2, right: 12, bottom: 2, left: 0 }}>
            <CartesianGrid stroke={CHART_GRIDLINE} horizontal={false} />
            <XAxis type="number" hide />
            <YAxis type="category" dataKey="agent" width={105} tick={{ fill: CHART_INK_MUTED, fontSize: 10 }} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={tooltipContentStyle} labelStyle={tooltipLabelStyle} formatter={(value, name, props) => [
              name === "revenue" ? currency.format(Number(value)) : `${value}%`,
              name === "revenue" ? `Revenue · Tier ${props.payload.tier}` : "Cumulative share",
            ]} />
            <Bar dataKey="revenue" name="revenue" radius={[0, 5, 5, 0]} barSize={15} cursor="pointer" onClick={(_entry, index) => { const agent = chartData[index]; if (agent) onSelectAgent?.(agent); }} isAnimationActive="auto" animationBegin={80} animationDuration={650} animationEasing="ease-out">
              {chartData.map((row) => <Cell key={row.agent} fill={TIER_COLORS[row.tier] ?? SEQUENTIAL_COLOR} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="agent-analysis">
        <div className="agent-tier-legend" aria-label="Agent Pareto tiers">
          <span><i className="tier-a" />A · first 80%</span>
          <span><i className="tier-b" />B · next 15%</span>
          <span><i className="tier-c" />C · remaining</span>
        </div>
        <ol className="agent-list">
          {chartData.map((row, index) => (
            <li className="agent-row" key={row.agent}><button type="button" className="agent-row-button" aria-label={`Explore ${row.agent} sales performance`} onClick={() => onSelectAgent?.(row)}>
              <div className="agent-row-heading">
                <span className="agent-rank">{String(index + 1).padStart(2, "0")}</span>
                <strong title={row.agent}>{row.agent}</strong>
                <span className={`agent-tier tier-${row.tier.toLowerCase()}`}>{row.tier}</span>
                <b>{currency.format(row.revenue)}</b>
              </div>
              <div className="agent-row-meta"><span>{row.transactions.toLocaleString("en-IN")} transactions · {currency.format(row.average_sale)} average sale</span><span>{row.share_pct}% of agent revenue</span></div>
              <div className="pareto-track" aria-label={`${row.cumulative_pct}% of named-agent revenue accounted for through this rank`}><span style={{ width: `${Math.min(row.cumulative_pct, 100)}%` }} /></div>
              <span className="pareto-caption">{row.cumulative_pct}% cumulative agent revenue</span>
            </button></li>
          ))}
        </ol>
      </div>
    </div>
  );
}
