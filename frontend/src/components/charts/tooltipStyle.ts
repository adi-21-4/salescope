import type { CSSProperties } from "react";
import { CHART_BASELINE, CHART_SURFACE } from "@/lib/chartColors";

export const tooltipContentStyle: CSSProperties = {
  background: CHART_SURFACE,
  border: `1px solid ${CHART_BASELINE}`,
  borderRadius: 6,
  fontSize: 12,
  padding: "8px 10px",
};

export const tooltipLabelStyle: CSSProperties = {
  color: "var(--chart-ink-primary)",
  fontWeight: 600,
  marginBottom: 4,
};
