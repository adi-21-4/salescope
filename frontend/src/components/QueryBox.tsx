import { useState, type FormEvent } from "react";
import { askQuestion, type NLQueryResult } from "@/api/query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import QueryResultChart from "@/components/charts/QueryResultChart";

interface Exchange {
  question: string;
  result: NLQueryResult | null;
  error: string | null;
}

interface Props {
  datasetId: string;
}

export default function QueryBox({ datasetId }: Props) {
  const [question, setQuestion] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [history, setHistory] = useState<Exchange[]>([]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const q = question.trim();
    if (!q || isLoading) return;
    setIsLoading(true);
    setQuestion("");
    try {
      const result = await askQuestion(datasetId, q);
      setHistory((prev) => [{ question: q, result, error: null }, ...prev]);
    } catch (err: any) {
      const message = err?.response?.data?.detail ?? "Could not answer that question";
      setHistory((prev) => [{ question: q, result: null, error: message }, ...prev]);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Ask your data</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="flex gap-2">
          <Input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g. What were my top 5 products last month?"
            disabled={isLoading}
          />
          <Button type="submit" disabled={isLoading || !question.trim()}>
            {isLoading ? "Asking…" : "Ask"}
          </Button>
        </form>

        {history.length > 0 && (
          <ul className="mt-4 space-y-4">
            {history.map((exchange, i) => (
              <li key={i} className="rounded-md border border-[hsl(var(--border))] p-3">
                <p className="text-sm font-medium">{exchange.question}</p>
                {exchange.error && (
                  <p className="mt-2 text-sm text-[hsl(var(--destructive))]">{exchange.error}</p>
                )}
                {exchange.result && (
                  <div className="mt-2">
                    <p className="text-sm text-[hsl(var(--muted-foreground))]">{exchange.result.answer_text}</p>
                    <div className="mt-2">
                      <QueryResultChart data={exchange.result.data} chartType={exchange.result.chart_type} />
                    </div>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
