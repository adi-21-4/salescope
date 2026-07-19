import { useEffect, useState } from "react";
import { getInsights, type InsightCard } from "@/api/insights";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

const CATEGORY_LABEL: Record<string, string> = {
  trend: "Trend",
  anomaly: "Anomaly",
  seasonality: "Seasonality",
  product: "Product",
  category: "Category",
  location: "Location",
  payment_method: "Payment",
};

interface Props {
  datasetId: string;
}

export default function InsightsPanel({ datasetId }: Props) {
  const [insights, setInsights] = useState<InsightCard[] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  function load(regenerate: boolean) {
    setIsLoading(true);
    setError(null);
    getInsights(datasetId, regenerate)
      .then(setInsights)
      .catch((err) => setError(err?.response?.data?.detail ?? "Could not generate insights"))
      .finally(() => setIsLoading(false));
  }

  useEffect(() => {
    load(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [datasetId]);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <CardTitle>AI insights</CardTitle>
        <Button variant="outline" onClick={() => load(true)} disabled={isLoading}>
          {isLoading ? "Thinking…" : "Regenerate"}
        </Button>
      </CardHeader>
      <CardContent>
        {isLoading && <p className="text-sm text-[hsl(var(--muted-foreground))]">Reading your sales data…</p>}
        {error && !isLoading && <p className="text-sm text-[hsl(var(--destructive))]">{error}</p>}
        {!isLoading && !error && insights && insights.length === 0 && (
          <p className="text-sm text-[hsl(var(--muted-foreground))]">No insights yet.</p>
        )}
        {!isLoading && !error && insights && insights.length > 0 && (
          <ul className="space-y-3">
            {insights.map((insight) => (
              <li key={insight.id} className="rounded-md border border-[hsl(var(--border))] p-3">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm font-medium">{insight.finding}</p>
                  <span className="shrink-0 rounded-full bg-[hsl(var(--muted))] px-2 py-0.5 text-xs">
                    {CATEGORY_LABEL[insight.category] ?? insight.category}
                  </span>
                </div>
                <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">{insight.supporting_stat}</p>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
