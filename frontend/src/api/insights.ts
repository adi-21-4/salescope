import { apiClient } from "./client";

export interface InsightCard {
  id: string;
  finding: string;
  supporting_stat: string;
  category: string;
  chart_ref: string | null;
  generated_at: string;
}

export async function getInsights(datasetId: string, regenerate = false) {
  const { data } = await apiClient.get<InsightCard[]>(`/datasets/${datasetId}/insights`, {
    params: regenerate ? { regenerate: true } : undefined,
  });
  return data;
}
