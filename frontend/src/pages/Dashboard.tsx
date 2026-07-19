import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { listDatasets } from "@/api/datasets";
import {
  getCategoryBreakdown,
  getDayOfWeekTrends,
  getForecast,
  getLocationBreakdown,
  getPaymentMethodBreakdown,
  getRevenueOverTime,
  getSeasonalTrends,
  getSummaryStats,
  getTopBottomProducts,
  type CategoryShare,
  type DayOfWeekPoint,
  type ForecastResponse,
  type LocationShare,
  type PaymentMethodShare,
  type ProductRevenue,
  type RevenueGranularity,
  type RevenuePoint,
  type SeasonalPoint,
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
import SeasonalChart from "@/components/charts/SeasonalChart";
import DimensionBreakdownChart from "@/components/charts/DimensionBreakdownChart";

interface DashboardData {
  summary: SummaryStats;
  topProducts: ProductRevenue[];
  bottomProducts: ProductRevenue[];
  dayOfWeek: DayOfWeekPoint[];
  seasonal: SeasonalPoint[];
  categories: CategoryShare[];
  locations: LocationShare[];
  paymentMethods: PaymentMethodShare[];
  forecast: ForecastResponse;
}

const GRANULARITY_OPTIONS: { value: RevenueGranularity; label: string }[] = [
  { value: "day", label: "Day" },
  { value: "week", label: "Week" },
  { value: "month", label: "Month" },
];

const currency = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });

export default function Dashboard() {
  const { datasetId } = useParams<{ datasetId: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<DashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [granularity, setGranularity] = useState<RevenueGranularity>("week");
  const [revenue, setRevenue] = useState<RevenuePoint[]>([]);
  const [isRevenueLoading, setIsRevenueLoading] = useState(false);
  const [revenueError, setRevenueError] = useState<string | null>(null);

  useEffect(() => {
    if (datasetId) return;
    // No dataset specified -> redirect to the most recently uploaded one that
    // actually has rows (a fully-deduped re-upload is "cleaned" but empty, and
    // would otherwise win here since datasets are returned most-recent-first).
    listDatasets().then((datasets) => {
      const ready = datasets.find((d) => d.status === "cleaned" && (d.row_count_clean ?? 0) > 0);
      if (ready) navigate(`/dashboard/${ready.id}`, { replace: true });
      else setIsLoading(false);
    });
  }, [datasetId, navigate]);

  useEffect(() => {
    if (!datasetId) return;
    setIsLoading(true);
    setError(null);
    Promise.all([
      getSummaryStats(datasetId),
      getTopBottomProducts(datasetId),
      getDayOfWeekTrends(datasetId),
      getSeasonalTrends(datasetId),
      getCategoryBreakdown(datasetId),
      getLocationBreakdown(datasetId),
      getPaymentMethodBreakdown(datasetId),
      getForecast(datasetId),
    ])
      .then(([summary, products, dayOfWeek, seasonal, categories, locations, paymentMethods, forecast]) => {
        setData({
          summary,
          topProducts: products.top,
          bottomProducts: products.bottom,
          dayOfWeek,
          seasonal,
          categories,
          locations,
          paymentMethods,
          forecast,
        });
      })
      .catch(() => setError("Could not load dashboard data"))
      .finally(() => setIsLoading(false));
  }, [datasetId]);

  useEffect(() => {
    if (!datasetId) return;
    setIsRevenueLoading(true);
    setRevenueError(null);
    getRevenueOverTime(datasetId, granularity)
      .then(setRevenue)
      .catch(() => setRevenueError("Could not load revenue data"))
      .finally(() => setIsRevenueLoading(false));
  }, [datasetId, granularity]);

  if (!datasetId && !isLoading) {
    return (
      <p className="text-sm text-[hsl(var(--muted-foreground))]">
        No dashboard yet.{" "}
        <Link to="/upload" className="text-[hsl(var(--primary))] hover:underline">
          Upload sales data
        </Link>{" "}
        to get started.
      </p>
    );
  }

  if (isLoading) return <p>Loading dashboard…</p>;
  if (error) return <p className="text-sm text-[hsl(var(--destructive))]">{error}</p>;
  if (!data) return null;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatTile label="Total revenue" value={currency.format(data.summary.total_revenue)} />
        <StatTile label="Total sales" value={data.summary.total_sales.toLocaleString()} />
        <StatTile label="Avg. sale value" value={currency.format(data.summary.avg_sale_value)} />
      </div>

      {datasetId && <InsightsPanel datasetId={datasetId} />}
      {datasetId && <QueryBox datasetId={datasetId} />}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between gap-4">
            <CardTitle>
              Revenue over time{granularity === "week" && data.forecast.points.length > 0 ? " + forecast" : ""}
            </CardTitle>
            <div className="flex gap-1 rounded-md border border-[hsl(var(--border))] p-0.5">
              {GRANULARITY_OPTIONS.map((opt) => (
                <Button
                  key={opt.value}
                  type="button"
                  variant={granularity === opt.value ? "primary" : "ghost"}
                  className="px-3 py-1 text-xs"
                  onClick={() => setGranularity(opt.value)}
                >
                  {opt.label}
                </Button>
              ))}
            </div>
          </CardHeader>
          <CardContent>
            {revenueError ? (
              <p className="text-sm text-[hsl(var(--destructive))]">{revenueError}</p>
            ) : (
              <>
                {/* Forecast points are always weekly, so only overlay them when the
                    chart itself is showing weekly buckets -- otherwise the dashed
                    line would bridge onto mismatched day/month periods. */}
                <RevenueLineChart
                  data={revenue}
                  forecast={granularity === "week" ? data.forecast.points : []}
                />
                {isRevenueLoading && (
                  <p className="mt-2 text-xs text-[hsl(var(--muted-foreground))]">Loading…</p>
                )}
                {granularity === "week" && data.forecast.points.length > 0 && (
                  <p className="mt-2 text-xs text-[hsl(var(--muted-foreground))]">{data.forecast.caveat}</p>
                )}
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Top products</CardTitle>
          </CardHeader>
          <CardContent>
            <ProductsBarChart data={data.topProducts} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Bottom products</CardTitle>
          </CardHeader>
          <CardContent>
            <ProductsBarChart
              data={data.bottomProducts}
              emptyMessage="Not enough distinct products to show a separate bottom list — see Top products above."
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Revenue by day of week</CardTitle>
          </CardHeader>
          <CardContent>
            <DayOfWeekChart data={data.dayOfWeek} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Seasonal trend (by month)</CardTitle>
          </CardHeader>
          <CardContent>
            <SeasonalChart data={data.seasonal} />
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Revenue by category</CardTitle>
          </CardHeader>
          <CardContent>
            <DimensionBreakdownChart
              data={data.categories.map((c) => ({ label: c.category, revenue: c.revenue, pct: c.pct }))}
              emptyMessage="No category data mapped."
            />
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Revenue by location / agent</CardTitle>
          </CardHeader>
          <CardContent>
            <DimensionBreakdownChart
              data={data.locations.map((l) => ({ label: l.location, revenue: l.revenue, pct: l.pct }))}
              emptyMessage="No location/agent data mapped."
            />
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Revenue by payment method</CardTitle>
          </CardHeader>
          <CardContent>
            <DimensionBreakdownChart
              data={data.paymentMethods.map((p) => ({
                label: p.payment_method,
                revenue: p.revenue,
                pct: p.pct,
              }))}
              emptyMessage="No payment method data mapped."
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
