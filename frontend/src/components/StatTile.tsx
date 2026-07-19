import { Card, CardContent } from "@/components/ui/card";

interface Props {
  label: string;
  value: string;
}

export default function StatTile({ label, value }: Props) {
  return (
    <Card>
      <CardContent className="p-5">
        <p className="text-sm text-[hsl(var(--muted-foreground))]">{label}</p>
        <p className="mt-1 text-3xl font-semibold tabular-nums">{value}</p>
      </CardContent>
    </Card>
  );
}
