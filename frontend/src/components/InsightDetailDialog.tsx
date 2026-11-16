import { useEffect, useRef } from "react";
import { ArrowUpRight, X } from "lucide-react";

export interface InsightDetail {
  id: string;
  category: string;
  title: string;
  summary: string;
  explanation: string;
  period: string;
  metricLabel: string;
  metricValue: number | null;
  valueFormat: "currency" | "percent" | "percentage_points";
  pointFormat: "currency" | "percent";
  chartRef: string | null;
  points: { label: string; value: number; compareValue?: number | null; marked?: boolean; note?: string | null }[];
  drivers: { label: string; dimension?: string; current: number; previous?: number; change?: number }[];
  suggestedQuestion?: string | null;
  stats?: { label: string; value: string }[];
  pointsLabel?: string;
  isLoading?: boolean;
  detailError?: string | null;
}

interface Props {
  insight: InsightDetail | null;
  onClose: () => void;
  onViewChart: (target: string) => void;
  onAskQuestion: (question: string) => void;
}

const currency = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });

function format(value: number, mode: "currency" | "percent" | "percentage_points") {
  if (mode === "currency") return currency.format(value);
  if (mode === "percentage_points") return `${value > 0 ? "+" : ""}${value.toFixed(1)} pp`;
  return `${value > 0 ? "+" : ""}${value.toFixed(1)}%`;
}

function formatPoint(value: number, mode: "currency" | "percent") {
  return mode === "currency" ? currency.format(value) : `${value.toFixed(1)}%`;
}

export default function InsightDetailDialog({ insight, onClose, onViewChart, onAskQuestion }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const isOpen = !!insight;
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (isOpen && !dialog.open) dialog.showModal();
    if (!isOpen && dialog.open) dialog.close();
  }, [isOpen]);

  if (!insight) return null;
  const paired = insight.points.some((point) => point.compareValue != null);
  const scale = Math.max(1, ...insight.points.flatMap((point) => [point.value, point.compareValue ?? 0]));

  return (
    <dialog ref={dialogRef} className="insight-dialog" aria-labelledby="insight-detail-title" onClose={onClose} onClick={(event) => { if (event.target === event.currentTarget) dialogRef.current?.close(); }}>
      <div className="insight-detail-shell">
        <header className="insight-detail-header">
          <div><span className="insight-detail-kicker">{insight.category.replaceAll("_", " ")} · {insight.period}</span><h2 id="insight-detail-title">{insight.title}</h2></div>
          <button className="insight-detail-close" type="button" aria-label="Close insight details" onClick={() => dialogRef.current?.close()}><X size={18} /></button>
        </header>
        <p className="insight-detail-summary">{insight.summary}</p>
        {insight.stats && <div className="agent-detail-stats">{insight.stats.map((stat) => <div key={stat.label}><span>{stat.label}</span><strong>{stat.value}</strong></div>)}</div>}
        {insight.metricValue != null && <div className="insight-detail-metric"><span>{insight.metricLabel}</span><strong>{format(insight.metricValue, insight.valueFormat)}</strong></div>}

        {insight.isLoading && <p className="agent-detail-loading" role="status"><i /> Loading this agent’s weekly trend and sales mix…</p>}
        {insight.detailError && <p className="agent-detail-error" role="status">{insight.detailError}</p>}
        {insight.points.length > 0 && <section className="insight-detail-section" aria-label="Supporting data">
          <div className="insight-detail-section-heading"><h3>{insight.pointsLabel ?? "What the data shows"}</h3>{paired && <span className="insight-detail-legend"><i /> Current <i className="compare-key" /> Previous</span>}</div>
          <ul className="insight-detail-points">{insight.points.map((point) => <li className={point.marked ? "is-marked" : ""} key={point.label}>
            <div className="insight-point-top"><span>{point.label}</span><strong>{formatPoint(point.value, insight.pointFormat)}</strong></div>
            {point.compareValue != null ? <div className="insight-paired-bars"><i style={{ width: `${Math.max(2, point.value / scale * 100)}%` }} /><i className="compare-bar" style={{ width: `${Math.max(2, point.compareValue / scale * 100)}%` }} /></div> : <div className="insight-paired-bars"><i style={{ width: `${Math.max(2, point.value / scale * 100)}%` }} /></div>}
            <div className="insight-point-foot">{point.compareValue != null && <span>Previous: {formatPoint(point.compareValue, insight.pointFormat)}</span>}{point.note && <span>{point.note}</span>}</div>
          </li>)}</ul>
        </section>}

        {insight.drivers.length > 0 && <section className="insight-detail-section">
          <div className="insight-detail-section-heading"><h3>{insight.category === "Sales agent" ? "Top products & categories" : "Largest revenue drivers"}</h3>{insight.category !== "Sales agent" && <span>current vs previous</span>}</div>
          <ul className="insight-driver-list">{insight.drivers.slice(0, 4).map((driver) => <li key={`${driver.dimension}-${driver.label}`}><span><strong>{driver.label}</strong><small>{(driver.dimension ?? "").replaceAll("_", " ")}</small></span><span>{currency.format(driver.current)}{driver.previous != null && <small>from {currency.format(driver.previous)}</small>}</span>{driver.change != null && <b className={driver.change >= 0 ? "change-positive" : "change-negative"}>{format(driver.change, "currency")}</b>}</li>)}</ul>
        </section>}

        <section className="insight-why"><strong>Why this appeared</strong><p>{insight.explanation}</p></section>
        <footer className="insight-detail-actions">
          {insight.chartRef && <button type="button" className="insight-secondary-action" onClick={() => onViewChart(insight.chartRef!)}>Show on dashboard <ArrowUpRight size={14} /></button>}
          {insight.suggestedQuestion && <button type="button" className="insight-primary-action" onClick={() => onAskQuestion(insight.suggestedQuestion!)}>Ask a follow-up <ArrowUpRight size={14} /></button>}
        </footer>
      </div>
    </dialog>
  );
}
