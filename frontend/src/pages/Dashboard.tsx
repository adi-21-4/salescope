import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowRight, CalendarDays, ChartNoAxesCombined, IndianRupee, Package, ReceiptText, ShoppingBag, Upload } from "lucide-react";
import { listDatasets } from "@/api/datasets";
import {
  getPerformanceHighlights,
  getAgentPerformance,
  getAgentDetail,
  getCategoryBreakdown,
  getDayOfWeekTrends,
  getForecast,
  getLocationBreakdown,
  getPaymentMethodBreakdown,
  getRevenueOverTime,
  getSummaryStats,
  getTopBottomProducts,
  type CategoryShare,
  type AgentPerformance,
  type DayOfWeekPoint,
  type ForecastResponse,
  type LocationShare,
  type PaymentMethodShare,
  type PerformanceHighlight,
  type ProductRevenue,
  type RevenueGranularity,
  type RevenuePoint,
  type SummaryStats,
} from "@/api/dashboard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import StatTile from "@/components/StatTile";
import InsightsPanel from "@/components/InsightsPanel";
import QueryBox from "@/components/QueryBox";
import RevenueLineChart from "@/components/charts/RevenueLineChart";
import ProductsBarChart from "@/components/charts/ProductsBarChart";
import DayOfWeekChart from "@/components/charts/DayOfWeekChart";
import MonthlyRevenueChart from "@/components/charts/MonthlyRevenueChart";
import DimensionBreakdownChart from "@/components/charts/DimensionBreakdownChart";
import RevenueMixDonutChart from "@/components/charts/RevenueMixDonutChart";
import AgentPerformanceChart from "@/components/charts/AgentPerformanceChart";
import InsightDetailDialog, { type InsightDetail } from "@/components/InsightDetailDialog";

interface DashboardData {
  summary: SummaryStats;
  topProducts: ProductRevenue[];
  bottomProducts: ProductRevenue[];
  dayOfWeek: DayOfWeekPoint[];
  monthlyRevenue: RevenuePoint[];
  categories: CategoryShare[];
  locations: LocationShare[];
  paymentMethods: PaymentMethodShare[];
  forecast: ForecastResponse;
  highlights: PerformanceHighlight[];
  agentPerformance: AgentPerformance[];
}

const GRANULARITY_OPTIONS: { value: RevenueGranularity; label: string }[] = [
  { value: "day", label: "Day" },
  { value: "week", label: "Week" },
  { value: "month", label: "Month" },
];

const currency = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });
const dateFormat = new Intl.DateTimeFormat("en-IN", { month: "short", day: "numeric", year: "numeric" });

function formatRange(start: string | null, end: string | null) {
  if (!start || !end) return "All available sales";
  const parseDate = (value: string) => new Date(`${value.slice(0, 10)}T00:00:00`);
  return `${dateFormat.format(parseDate(start))} – ${dateFormat.format(parseDate(end))}`;
}

export default function Dashboard() {
  const { datasetId } = useParams<{ datasetId: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<DashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [granularity, setGranularity] = useState<RevenueGranularity>("week");
  const [revenueView, setRevenueView] = useState<{ granularity: RevenueGranularity; points: RevenuePoint[]; datasetId: string } | null>(null);
  const [isRevenueLoading, setIsRevenueLoading] = useState(false);
  const [revenueError, setRevenueError] = useState<string | null>(null);
  const [selectedInsight, setSelectedInsight] = useState<InsightDetail | null>(null);
  const [querySuggestion, setQuerySuggestion] = useState<{ id: number; question: string } | null>(null);

  useEffect(() => {
    if (datasetId) return;
    listDatasets()
      .then((datasets) => {
        const ready = datasets.find((d) => d.status === "cleaned" && (d.row_count_clean ?? 0) > 0);
        if (ready) navigate(`/dashboard/${ready.id}`, { replace: true });
        else setIsLoading(false);
      })
      .catch(() => {
        setError("Could not load your sales data. Check the connection and try again.");
        setIsLoading(false);
      });
  }, [datasetId, navigate]);

  useEffect(() => {
    if (!datasetId) return;
    let active = true;
    setIsLoading(true);
    setError(null);
    Promise.all([
      getSummaryStats(datasetId),
      getTopBottomProducts(datasetId),
      getDayOfWeekTrends(datasetId),
      getRevenueOverTime(datasetId, "month"),
      getCategoryBreakdown(datasetId),
      getLocationBreakdown(datasetId),
      getPaymentMethodBreakdown(datasetId),
      getForecast(datasetId),
      getPerformanceHighlights(datasetId),
      getAgentPerformance(datasetId),
    ])
    .then(([summary, products, dayOfWeek, monthlyRevenue, categories, locations, paymentMethods, forecast, highlights, agentPerformance]) => {
        if (!active) return;
        setData({
          summary,
          topProducts: products.top,
          bottomProducts: products.bottom,
          dayOfWeek,
          monthlyRevenue,
          categories,
          locations,
          paymentMethods,
          forecast,
          highlights,
          agentPerformance,
        });
      })
      .catch(() => { if (active) setError("Could not load dashboard data"); })
      .finally(() => { if (active) setIsLoading(false); });
    return () => { active = false; };
  }, [datasetId]);

  useEffect(() => {
    if (!datasetId) return;
    let active = true;
    setIsRevenueLoading(true);
    setRevenueError(null);
    getRevenueOverTime(datasetId, granularity)
    .then((points) => { if (active) setRevenueView({ granularity, points, datasetId }); })
      .catch(() => { if (active) setRevenueError("Could not load revenue data"); })
      .finally(() => { if (active) setIsRevenueLoading(false); });
    return () => { active = false; };
  }, [datasetId, granularity]);

  if (isLoading) {
    return (
      <div className="dashboard-loading" role="status" aria-label="Loading sales overview">
        <div className="loading-topline"><span className="loading-mark"><ChartNoAxesCombined size={18} /></span><span className="loading-line loading-line-short" /></div>
        <div className="loading-metrics"><span /><span /><span /></div>
        <div className="loading-chart"><i /><i /><i /><i /><i /><i /></div>
        <p>Preparing your sales overview…</p>
      </div>
    );
  }

  if (error) {
    return <div className="dashboard-error" role="alert"><p>{error}</p><Button variant="outline" onClick={() => window.location.reload()}>Try again</Button></div>;
  }

  if (!datasetId || !data) {
    return (
      <div className="dashboard-empty">
        <div className="empty-mark"><ShoppingBag size={23} /></div>
        <p className="dashboard-eyebrow">Start with your sales data</p>
        <h1>Your next decision starts here.</h1>
        <p>Upload a sales export to see revenue, product performance, and patterns across your shop.</p>
        <Link to="/upload" className="dashboard-action"><Upload size={16} /> Import sales data <ArrowRight size={16} /></Link>
      </div>
    );
  }

  const firstForecast = data.forecast.points[0];
  const hasForecast = data.forecast.method !== "insufficient_data" && !!firstForecast;
  const hasRevenueView = revenueView?.datasetId === datasetId;
  const visibleRevenue = hasRevenueView ? revenueView : null;

  return (
    <div className="dashboard-page">
      <header className="dashboard-heading">
        <div className="dashboard-title-block">
          <h1>Sales overview</h1>
          <p className="dashboard-subtitle">Track what sold, how much it earned, and where it came from.</p>
        </div>
        <div className="dashboard-heading-actions">
          <div className="date-range"><CalendarDays size={15} /><span>{formatRange(data.summary.date_range_start, data.summary.date_range_end)}</span></div>
          <Link to="/upload" className="dashboard-action"><Upload size={15} /><span>Import sales</span></Link>
        </div>
      </header>

      {data.highlights.length > 0 && <section className="signal-strip" aria-label="Quick sales insights">
        <h2 className="signal-strip-heading">Quick read</h2>
        <div className="signal-grid">{data.highlights.map((highlight) => <article className="signal-card" key={highlight.kind}>
          <div><p>{highlight.label}</p><strong title={highlight.value}>{highlight.value}</strong><small>{highlight.detail}</small></div>
        </article>)}</div>
      </section>}

      <section className={`summary-grid${data.summary.gross_profit != null ? " has-profit" : ""}`} aria-label="Sales summary">
        <StatTile label="Revenue" value={currency.format(data.summary.total_revenue)} note="All included sales" icon={IndianRupee} tone="green" />
        <StatTile label="Transactions" value={data.summary.total_sales.toLocaleString("en-IN")} note="Completed sales" icon={ReceiptText} tone="blue" />
        <StatTile label="Average sale" value={currency.format(data.summary.avg_sale_value)} note="Revenue per transaction" icon={ChartNoAxesCombined} tone="gold" />
        <StatTile label="Units sold" value={new Intl.NumberFormat("en-IN", { maximumFractionDigits: 1 }).format(data.summary.total_units)} note="Quantity across sales" icon={Package} tone="green" />
        {data.summary.gross_profit != null && <StatTile label="Gross profit" value={currency.format(data.summary.gross_profit)} note={`${data.summary.gross_margin_pct ?? 0}% gross margin · cost data for ${data.summary.cost_coverage_pct}% of revenue`} icon={IndianRupee} tone="blue" />}
      </section>

      <section className="dashboard-primary-grid" aria-label="Revenue and forecast">
        <Card id="revenue-chart" className="dashboard-card revenue-card">
          <CardHeader className="dashboard-card-header">
            <CardTitle>Revenue over time</CardTitle>
            <div className="granularity-switch" role="group" aria-label="Revenue chart interval">
              {GRANULARITY_OPTIONS.map((option) => (
                <Button key={option.value} type="button" variant={granularity === option.value ? "primary" : "ghost"} className={granularity === option.value ? "granularity-button is-selected" : "granularity-button"} aria-pressed={granularity === option.value} onClick={() => setGranularity(option.value)}>{option.label}</Button>
              ))}
            </div>
          </CardHeader>
          <CardContent className="dashboard-card-content">
            <div className={`revenue-chart-stage${isRevenueLoading ? " is-loading" : " is-ready"}`} aria-busy={isRevenueLoading}>
              {revenueError ? <p className="chart-message" role="alert">{revenueError}</p> : !hasRevenueView && isRevenueLoading ? (
                <div className="revenue-chart-skeleton" aria-hidden="true"><span /><span /><span /><span /><span /><i /></div>
              ) : (
                <div className="revenue-chart-view" key={`${datasetId}-${visibleRevenue?.granularity}`}><RevenueLineChart data={visibleRevenue?.points ?? []} forecast={visibleRevenue?.granularity === "week" ? data.forecast.points : []} /></div>
              )}
              {isRevenueLoading && hasRevenueView && <span className="chart-loading-pill" role="status"><i /> Loading {granularity} view</span>}
            </div>
            {!isRevenueLoading && visibleRevenue?.granularity === "week" && data.forecast.points.length > 0 && <p className="chart-footnote"><span className="forecast-key" />Dashed line shows your forecast</p>}
          </CardContent>
        </Card>

        <Card className="dashboard-card forecast-card">
          <CardHeader className="dashboard-card-header forecast-heading">
            <CardTitle>Revenue forecast</CardTitle>
          </CardHeader>
          <CardContent className="dashboard-card-content forecast-content">
            {hasForecast ? <><p className="forecast-label">Next week</p><p className="forecast-value">{currency.format(firstForecast.revenue)}</p></> : <p className="forecast-empty-title">More sales history is needed for a forecast.</p>}
            <p className="forecast-caveat">{data.forecast.caveat}</p>
          </CardContent>
        </Card>
      </section>

      <section className="dashboard-insights-grid" aria-label="Insights and questions">
        <InsightsPanel datasetId={datasetId} className="dashboard-card insight-card" onInsightClick={setSelectedInsight} />
        <QueryBox datasetId={datasetId} className="dashboard-card query-card" suggestedQuestion={querySuggestion} />
      </section>

      <section id="product-charts" className="chart-grid chart-grid-products" aria-label="Product performance">
        <Card className="dashboard-card chart-card"><CardHeader className="dashboard-card-header"><CardTitle>Top products</CardTitle></CardHeader><CardContent className="dashboard-card-content"><ProductsBarChart data={data.topProducts} /></CardContent></Card>
        <Card className="dashboard-card chart-card"><CardHeader className="dashboard-card-header"><CardTitle>Lowest-revenue products</CardTitle></CardHeader><CardContent className="dashboard-card-content"><ProductsBarChart data={data.bottomProducts} emptyMessage="Not enough products to compare." /></CardContent></Card>
      </section>

      <section className="agent-section" aria-label="Sales agent performance">
        <Card id="agent-performance" className="dashboard-card agent-card">
          <CardHeader className="dashboard-card-header agent-card-header"><div><CardTitle>Sales by agent</CardTitle><p className="agent-card-description">Choose an agent to see weekly revenue and product mix.</p></div><span className="agent-heading-mark"><ChartNoAxesCombined size={17} /></span></CardHeader>
          <CardContent className="dashboard-card-content agent-card-content"><AgentPerformanceChart data={data.agentPerformance} onSelectAgent={(agent) => {
            setSelectedInsight({
              id: `agent-${agent.agent}`, category: "Sales agent", title: `${agent.agent} · performance detail`,
              summary: `${currency.format(agent.revenue)} in recorded revenue from ${agent.transactions.toLocaleString("en-IN")} transactions.`,
              explanation: `A, B, and C group agents by cumulative revenue contribution: A covers the first ~80%, B the next ~15%, and C the remainder.`,
              period: formatRange(data.summary.date_range_start, data.summary.date_range_end), metricLabel: "Share of agent revenue", metricValue: agent.share_pct,
              valueFormat: "percent", pointFormat: "currency", chartRef: "agent-performance", points: [], pointsLabel: "Weekly revenue",
              stats: [
                { label: "Recorded revenue", value: currency.format(agent.revenue) },
                { label: "Transactions", value: agent.transactions.toLocaleString("en-IN") },
                { label: "Average sale", value: currency.format(agent.average_sale) },
              ],
              drivers: [], isLoading: true, suggestedQuestion: `What are the top products sold by ${agent.agent}?`,
            });
            getAgentDetail(datasetId, agent.agent).then((detail) => setSelectedInsight((current) => current?.id === `agent-${agent.agent}` ? {
              ...current,
              isLoading: false,
              points: detail.weekly_revenue.slice(-12).map((point) => ({ label: point.period, value: point.revenue })),
              drivers: [
                ...detail.top_products.slice(0, 2).map((product) => ({ label: product.product, dimension: "top product", current: product.revenue })),
                ...detail.categories.slice(0, 2).map((category) => ({ label: category.category, dimension: "category mix", current: category.revenue })),
              ],
            } : current)).catch(() => setSelectedInsight((current) => current?.id === `agent-${agent.agent}` ? { ...current, isLoading: false, detailError: "The agent detail could not be loaded. Close this panel and try again." } : current));
          }} /></CardContent>
        </Card>
      </section>

      <section id="sales-patterns" className="chart-grid" aria-label="Sales patterns">
        <Card className="dashboard-card chart-card"><CardHeader className="dashboard-card-header"><CardTitle>Average daily revenue by weekday</CardTitle></CardHeader><CardContent className="dashboard-card-content"><DayOfWeekChart data={data.dayOfWeek} /></CardContent></Card>
        <Card className="dashboard-card chart-card"><CardHeader className="dashboard-card-header"><CardTitle>Revenue by month</CardTitle></CardHeader><CardContent className="dashboard-card-content"><MonthlyRevenueChart data={data.monthlyRevenue} /></CardContent></Card>
      </section>

      <section id="sales-breakdowns" className="chart-grid chart-grid-breakdowns" aria-label="Sales breakdowns">
        <Card className="dashboard-card breakdown-card breakdown-card--donut"><CardHeader className="dashboard-card-header"><CardTitle>Revenue by category</CardTitle></CardHeader><CardContent className="dashboard-card-content"><RevenueMixDonutChart data={data.categories.map((category) => ({ label: category.category, revenue: category.revenue, pct: category.pct }))} emptyMessage="No category data mapped." /></CardContent></Card>
        <Card className="dashboard-card breakdown-card"><CardHeader className="dashboard-card-header"><CardTitle>Revenue by location</CardTitle></CardHeader><CardContent className="dashboard-card-content"><DimensionBreakdownChart data={data.locations.map((location) => ({ label: location.location, revenue: location.revenue, pct: location.pct }))} emptyMessage="No location data mapped." /></CardContent></Card>
        <Card className="dashboard-card breakdown-card breakdown-card--donut"><CardHeader className="dashboard-card-header"><CardTitle>Revenue by payment method</CardTitle></CardHeader><CardContent className="dashboard-card-content"><RevenueMixDonutChart data={data.paymentMethods.map((payment) => ({ label: payment.payment_method, revenue: payment.revenue, pct: payment.pct }))} emptyMessage="No payment method data mapped." /></CardContent></Card>
      </section>

      <footer className="dashboard-footer"><span>SalesScope · Retail analytics</span><span><span className="footer-status-dot" />Built from your sales data</span></footer>
      <InsightDetailDialog
        insight={selectedInsight}
        onClose={() => setSelectedInsight(null)}
        onViewChart={(target) => { setSelectedInsight(null); window.setTimeout(() => document.getElementById(target)?.scrollIntoView({ behavior: "smooth", block: "center" }), 80); }}
        onAskQuestion={(question) => { setSelectedInsight(null); setQuerySuggestion((current) => ({ id: (current?.id ?? 0) + 1, question })); }}
      />
    </div>
  );
}
