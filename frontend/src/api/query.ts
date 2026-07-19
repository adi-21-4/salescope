import { apiClient } from "./client";

export interface NLDataPoint {
  label: string;
  value: number;
}

export interface NLQueryResult {
  answer_text: string;
  data: NLDataPoint[];
  chart_type: "line" | "bar" | "number";
}

export async function askQuestion(datasetId: string, question: string) {
  const { data } = await apiClient.post<NLQueryResult>(`/datasets/${datasetId}/query`, { question });
  return data;
}
