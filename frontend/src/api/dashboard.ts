import { apiClient } from "./client";

export interface RevenuePoint {
  period: string;
  revenue: number;
}

export interface ProductRevenue {
  product: string;
  revenue: number;
}

export interface TopBottomProducts {
  top: ProductRevenue[];
  bottom: ProductRevenue[];
}

export interface DayOfWeekPoint {
  day: string;
  avg_revenue: number;
}

export interface SeasonalPoint {
  month: string;
  avg_revenue: number;
}

export interface CategoryShare {
  category: string;
  revenue: number;
  pct: number;
}

export interface LocationShare {
  location: string;
  revenue: number;
  pct: number;
}

export interface PaymentMethodShare {
  payment_method: string;
  revenue: number;
  pct: number;
}

export type ForecastMethod = "insufficient_data" | "linear_trend" | "holt_winters_trend" | "holt_winters_seasonal";

export interface ForecastResponse {
  method: ForecastMethod;
  points: RevenuePoint[];
  caveat: string;
}

export interface SummaryStats {
  total_revenue: number;
  total_sales: number;
  avg_sale_value: number;
  total_units: number;
  gross_profit: number | null;
  gross_margin_pct: number | null;
  cost_coverage_pct: number;
  date_range_start: string | null;
  date_range_end: string | null;
}

export interface PerformanceHighlight {
  kind: "product" | "category" | "location" | "weekday";
  label: string;
  value: string;
  detail: string;
}

export interface AgentPerformance {
  agent: string;
  revenue: number;
  transactions: number;
  average_sale: number;
  share_pct: number;
  cumulative_pct: number;
  tier: "A" | "B" | "C";
}

export interface AgentDetail {
  agent: string;
  revenue: number;
  transactions: number;
  average_sale: number;
  share_pct: number;
  weekly_revenue: RevenuePoint[];
  top_products: ProductRevenue[];
  categories: CategoryShare[];
}

export interface ActionableInsightPoint {
  label: string;
  value: number;
  compare_value: number | null;
  marked: boolean;
  note: string | null;
}

export interface InsightDriver {
  label: string;
  dimension: string;
  current: number;
  previous: number;
  change: number;
}

export interface ActionableInsight {
  id: "revenue_change" | "sales_anomaly" | "product_concentration" | "payment_shift" | "location_shift";
  category: string;
  title: string;
  summary: string;
  explanation: string;
  period: string;
  metric_label: string;
  metric_value: number;
  value_format: "currency" | "percent" | "percentage_points";
  point_format: "currency" | "percent";
  chart_ref: string | null;
  points: ActionableInsightPoint[];
  drivers: InsightDriver[];
  suggested_question: string | null;
}

export async function getSummaryStats(datasetId: string) {
  const { data } = await apiClient.get<SummaryStats>(`/dashboard/${datasetId}/summary`);
  return data;
}

export async function getPerformanceHighlights(datasetId: string) {
  const { data } = await apiClient.get<PerformanceHighlight[]>(`/dashboard/${datasetId}/highlights`);
  return data;
}

export async function getAgentPerformance(datasetId: string, limit = 20) {
  const { data } = await apiClient.get<AgentPerformance[]>(`/dashboard/${datasetId}/agent-performance`, {
    params: { limit },
  });
  return data;
}

export async function getAgentDetail(datasetId: string, agent: string) {
  const { data } = await apiClient.get<AgentDetail>(`/dashboard/${datasetId}/agent-detail`, { params: { agent } });
  return data;
}

export async function getActionableInsights(datasetId: string) {
  const { data } = await apiClient.get<ActionableInsight[]>(`/dashboard/${datasetId}/actionable-insights`);
  return data;
}

export type RevenueGranularity = "day" | "week" | "month";

export async function getRevenueOverTime(datasetId: string, granularity: RevenueGranularity = "week") {
  const { data } = await apiClient.get<RevenuePoint[]>(`/dashboard/${datasetId}/revenue`, {
    params: { granularity },
  });
  return data;
}

export async function getTopBottomProducts(datasetId: string, n = 10) {
  const { data } = await apiClient.get<TopBottomProducts>(`/dashboard/${datasetId}/top-products`, {
    params: { n },
  });
  return data;
}

export async function getDayOfWeekTrends(datasetId: string) {
  const { data } = await apiClient.get<DayOfWeekPoint[]>(`/dashboard/${datasetId}/day-of-week`);
  return data;
}

export async function getSeasonalTrends(datasetId: string) {
  const { data } = await apiClient.get<SeasonalPoint[]>(`/dashboard/${datasetId}/seasonality`);
  return data;
}

export async function getCategoryBreakdown(datasetId: string) {
  const { data } = await apiClient.get<CategoryShare[]>(`/dashboard/${datasetId}/category-breakdown`);
  return data;
}

export async function getLocationBreakdown(datasetId: string) {
  const { data } = await apiClient.get<LocationShare[]>(`/dashboard/${datasetId}/location-breakdown`);
  return data;
}

export async function getPaymentMethodBreakdown(datasetId: string) {
  const { data } = await apiClient.get<PaymentMethodShare[]>(`/dashboard/${datasetId}/payment-method-breakdown`);
  return data;
}

export async function getForecast(datasetId: string, horizonWeeks = 4) {
  const { data } = await apiClient.get<ForecastResponse>(`/dashboard/${datasetId}/forecast`, {
    params: { horizon_weeks: horizonWeeks },
  });
  return data;
}
