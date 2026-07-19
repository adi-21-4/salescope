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
  date_range_start: string | null;
  date_range_end: string | null;
}

export async function getSummaryStats(datasetId: string) {
  const { data } = await apiClient.get<SummaryStats>(`/dashboard/${datasetId}/summary`);
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
