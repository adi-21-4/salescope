import { useEffect, useState } from "react";
import { ArrowUpRight, Sparkles } from "lucide-react";
import { getInsights, type InsightCard } from "@/api/insights";
import { getActionableInsights, type ActionableInsight } from "@/api/dashboard";
import type { InsightDetail } from "@/components/InsightDetailDialog";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

const CATEGORY_LABEL: Record<string, string> = {
  trend: "Trend",
  anomaly: "Anomaly",
  seasonality: "Seasonality",
  product: "Product",
  category: "Category",
  location: "Store",
  agent: "Agent",
  payment_method: "Payment",
  profit: "Margin",
  retention: "Retention",
};

interface Props {
  datasetId: string;
  className?: string;
  onInsightClick: (insight: InsightDetail) => void;
}

export default function InsightsPanel({ datasetId, className = "", onInsightClick }: Props) {
  const [insights, setInsights] = useState<InsightCard[] | null>(null);
  const [actionable, setActionable] = useState<ActionableInsight[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  function load(regenerate: boolean) {
    setIsLoading(true);
    setError(null);
    Promise.allSettled([getInsights(datasetId, regenerate), getActionableInsights(datasetId)])
      .then(([aiResult, dataResult]) => {
        if (aiResult.status === "fulfilled") setInsights(aiResult.value);
        else setError(aiResult.reason?.response?.data?.detail ?? "AI notes are unavailable right now");
        if (dataResult.status === "fulfilled") setActionable(dataResult.value);
      })
      .finally(() => setIsLoading(false));
  }

  useEffect(() => {
    load(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [datasetId]);

  return (
    <Card className={className} id="insights">
      <CardHeader className="dashboard-card-header insight-header">
        <CardTitle><Sparkles size={16} />Sales insights</CardTitle>
        <Button className="quiet-action" variant="outline" onClick={() => load(true)} disabled={isLoading}>
          {isLoading ? "Refreshing…" : "Refresh"}
        </Button>
      </CardHeader>
      <CardContent className="dashboard-card-content insight-content">
        {isLoading && actionable.length === 0 && <p className="insights-loading" role="status">Finding changes and outliers…</p>}
        {error && !isLoading && actionable.length === 0 && <p className="text-sm text-[hsl(var(--destructive))]" role="alert">{error}</p>}
        {!isLoading && !error && insights?.length === 0 && actionable.length === 0 && (
          <p className="text-sm text-[hsl(var(--muted-foreground))]">No notable changes found yet.</p>
        )}
        {((insights?.length ?? 0) > 0 || actionable.length > 0) && <ul className="insight-list">
          {actionable.map((insight) => <li className="insight-item" key={insight.id}>
            <button type="button" className="insight-item-button" aria-label={`Open insight: ${insight.title}`} onClick={() => onInsightClick(toInsightDetail(insight))}>
              <div className="insight-item-head"><p>{insight.title}</p><span className="insight-category">{CATEGORY_LABEL[insight.category] ?? insight.category}</span></div>
              <p className="insight-support">{insight.summary}</p><ArrowUpRight className="insight-open-cue" size={15} aria-hidden="true" />
            </button>
          </li>)}
          {(insights ?? []).map((insight) => <li className="insight-item" key={insight.id}>
            <button type="button" className="insight-item-button" aria-label={`Open insight: ${insight.finding}`} onClick={() => onInsightClick(toAiDetail(insight))}>
              <div className="insight-item-head"><p>{insight.finding}</p><span className="insight-category">{CATEGORY_LABEL[insight.category] ?? insight.category}</span></div>
              <p className="insight-support">{insight.supporting_stat}</p><ArrowUpRight className="insight-open-cue" size={15} aria-hidden="true" />
            </button>
          </li>)}
        </ul>}
      </CardContent>
    </Card>
  );
}

function toInsightDetail(insight: ActionableInsight): InsightDetail {
  return {
    id: insight.id, category: insight.category, title: insight.title, summary: insight.summary,
    explanation: insight.explanation, period: insight.period, metricLabel: insight.metric_label,
    metricValue: insight.metric_value, valueFormat: insight.value_format, pointFormat: insight.point_format,
    chartRef: insight.chart_ref, points: insight.points.map((point) => ({ label: point.label, value: point.value, compareValue: point.compare_value, marked: point.marked, note: point.note })),
    drivers: insight.drivers.map((driver) => ({ label: driver.label, dimension: driver.dimension, current: driver.current, previous: driver.previous, change: driver.change })),
    suggestedQuestion: insight.suggested_question,
  };
}

function toAiDetail(insight: InsightCard): InsightDetail {
  const questions: Record<string, string> = {
    product: "What are my top products by revenue?", category: "What are my top categories by revenue?",
    location: "What locations have the most revenue?", agent: "Which sales agents had the most revenue?",
    payment_method: "What was revenue by payment method?", trend: "Show revenue by week.",
  };
  return {
    id: `ai-${insight.id}`, category: insight.category, title: insight.finding, summary: insight.supporting_stat,
    explanation: "Interpretation generated from this dataset’s sales totals. Open the linked chart to inspect the supporting values.",
    period: `Generated ${new Date(insight.generated_at).toLocaleDateString()}`, metricLabel: "Supporting statistic", metricValue: null,
    valueFormat: "currency", pointFormat: "currency", chartRef: insight.chart_ref === "agent_performance" ? "agent-performance" : insight.chart_ref === "top_products" ? "product-charts" : insight.chart_ref === "category_breakdown" || insight.chart_ref === "location_breakdown" || insight.chart_ref === "payment_method_breakdown" ? "sales-breakdowns" : insight.chart_ref === "day_of_week" || insight.chart_ref === "seasonality" ? "sales-patterns" : "revenue-chart",
    points: [], drivers: [], suggestedQuestion: questions[insight.category],
  };
}
