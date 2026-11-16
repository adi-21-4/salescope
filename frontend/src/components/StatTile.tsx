import type { LucideIcon } from "lucide-react";
import { Card } from "@/components/ui/card";

interface Props {
  label: string;
  value: string;
  note: string;
  icon: LucideIcon;
  tone: "green" | "blue" | "gold";
}

export default function StatTile({ label, value, note, icon: Icon, tone }: Props) {
  return (
    <Card className={`dashboard-card metric-card metric-card--${tone}`}>
      <div className="metric-heading"><span className="metric-label">{label}</span><span className="metric-icon"><Icon size={17} strokeWidth={1.9} /></span></div>
      <p className="metric-value">{value}</p>
      <p className="metric-note">{note}</p>
      <span className="metric-rule" aria-hidden="true" />
    </Card>
  );
}
