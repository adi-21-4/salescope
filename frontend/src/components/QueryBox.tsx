import { useEffect, useRef, useState, type FormEvent } from "react";
import { ArrowUpRight, MessageSquareText } from "lucide-react";
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
  className?: string;
  suggestedQuestion?: { id: number; question: string } | null;
}

export default function QueryBox({ datasetId, className = "", suggestedQuestion = null }: Props) {
  const [question, setQuestion] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [history, setHistory] = useState<Exchange[]>([]);

  useEffect(() => {
    if (!suggestedQuestion) return;
    setQuestion(suggestedQuestion.question);
    document.getElementById("ask-your-data")?.scrollIntoView({ behavior: "smooth", block: "center" });
    window.setTimeout(() => inputRef.current?.focus(), 220);
  }, [suggestedQuestion]);

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
    <Card className={className} id="ask-your-data">
      <CardHeader className="dashboard-card-header query-header">
        <CardTitle><MessageSquareText size={17} />Ask your data</CardTitle>
      </CardHeader>
      <CardContent className="dashboard-card-content query-content">
        <form onSubmit={handleSubmit} className="query-form">
          <Input
            ref={inputRef}
            id="sales-query"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Which products earned the most last month?"
            disabled={isLoading}
            aria-label="Ask a question about your sales data"
          />
          <Button className="query-submit" type="submit" disabled={isLoading || !question.trim()}>
            {isLoading ? "Asking…" : <><span>Ask</span><ArrowUpRight size={15} /></>}
          </Button>
        </form>

        {history.length > 0 && (
          <ul className="query-history">
            {history.map((exchange, i) => (
              <li key={i} className="query-exchange">
                <p className="query-question">{exchange.question}</p>
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
