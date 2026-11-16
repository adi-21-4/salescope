import { apiClient } from "./client";

export type DatasetStatus =
  | "uploaded"
  | "mapping_pending"
  | "mapping_confirmed"
  | "cleaned"
  | "failed";

export interface UploadedDataset {
  id: string;
  original_filename: string;
  file_type: string;
  status: DatasetStatus;
  row_count_raw: number | null;
  row_count_clean: number | null;
  uploaded_at: string;
}

export async function uploadDataset(file: File, onProgress?: (pct: number) => void) {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await apiClient.post<UploadedDataset>("/datasets/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (event) => {
      if (onProgress && event.total) onProgress(Math.round((event.loaded / event.total) * 100));
    },
  });
  return data;
}

export async function listDatasets() {
  const { data } = await apiClient.get<UploadedDataset[]>("/datasets");
  return data;
}

export async function getDataset(id: string) {
  const { data } = await apiClient.get<UploadedDataset>(`/datasets/${id}`);
  return data;
}

export type ColumnRole =
  | "date"
  | "product"
  | "quantity"
  | "price"
  | "unit_cost"
  | "line_total"
  | "category"
  | "status"
  | "location"
  | "agent"
  | "customer_id"
  | "payment_method";
export type MappingRole = ColumnRole | "ignore";

export interface RoleCandidate {
  role: ColumnRole;
  confidence: number;
}

export interface ColumnDetection {
  column: string;
  detected_role: ColumnRole | null;
  confidence: number;
  candidates: RoleCandidate[];
  sample_values: string[];
  distinct_values: string[];
}

export interface DatasetPreview {
  dataset_id: string;
  columns: ColumnDetection[];
}

export interface ConfirmMappingResult {
  dataset_id: string;
  status: DatasetStatus;
  rows_total: number;
  rows_clean: number;
  invalid_date_count: number;
  excluded_by_status_count: number;
  incomplete_count: number;
  duplicate_count: number;
  already_existed_count: number;
}

export async function previewDataset(id: string) {
  const { data } = await apiClient.get<DatasetPreview>(`/datasets/${id}/preview`);
  return data;
}

export async function confirmMapping(
  id: string,
  mapping: Record<string, MappingRole>,
  includedStatusValues?: string[] | null
) {
  const { data } = await apiClient.post<ConfirmMappingResult>(`/datasets/${id}/confirm-mapping`, {
    mapping,
    included_status_values: includedStatusValues ?? null,
  });
  return data;
}
