import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { listDatasets, uploadDataset, type UploadedDataset } from "@/api/datasets";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const STATUS_LABEL: Record<UploadedDataset["status"], string> = {
  uploaded: "Uploaded",
  mapping_pending: "Needs column review",
  mapping_confirmed: "Mapping confirmed",
  cleaned: "Ready",
  failed: "Failed",
};

export default function Upload() {
  const navigate = useNavigate();
  const [datasets, setDatasets] = useState<UploadedDataset[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const refreshDatasets = useCallback(() => {
    listDatasets().then(setDatasets).catch(() => setError("Could not load past uploads"));
  }, []);

  useEffect(() => {
    refreshDatasets();
  }, [refreshDatasets]);

  async function handleFile(file: File) {
    setError(null);
    setIsUploading(true);
    setProgress(0);
    try {
      const dataset = await uploadDataset(file, setProgress);
      navigate(`/datasets/${dataset.id}/mapping`);
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Upload failed");
    } finally {
      setIsUploading(false);
    }
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Upload sales data</CardTitle>
        </CardHeader>
        <CardContent>
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={onDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-10 text-center transition-colors ${
              isDragging ? "border-[hsl(var(--primary))] bg-[hsl(var(--muted))]" : "border-[hsl(var(--border))]"
            }`}
          >
            <p className="font-medium">Drag & drop a CSV or Excel file here</p>
            <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">or click to browse</p>
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.xlsx,.xls"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleFile(file);
                e.target.value = "";
              }}
            />
          </div>
          {isUploading && (
            <div className="mt-4">
              <div className="h-2 w-full overflow-hidden rounded-full bg-[hsl(var(--muted))]">
                <div
                  className="h-full bg-[hsl(var(--primary))] transition-all"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">Uploading… {progress}%</p>
            </div>
          )}
          {error && <p className="mt-4 text-sm text-[hsl(var(--destructive))]">{error}</p>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Past uploads</CardTitle>
        </CardHeader>
        <CardContent>
          {datasets.length === 0 ? (
            <p className="text-sm text-[hsl(var(--muted-foreground))]">No uploads yet.</p>
          ) : (
            <ul className="divide-y divide-[hsl(var(--border))]">
              {datasets.map((d) => (
                <li key={d.id} className="flex items-center justify-between py-3 text-sm">
                  <div>
                    <p className="font-medium">{d.original_filename}</p>
                    <p className="text-[hsl(var(--muted-foreground))]">
                      {d.status === "cleaned"
                        ? `${d.row_count_clean ?? 0} of ${d.row_count_raw ?? "?"} rows`
                        : `${d.row_count_raw ?? "?"} rows`}{" "}
                      · {new Date(d.uploaded_at).toLocaleString()}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="rounded-full bg-[hsl(var(--muted))] px-3 py-1 text-xs">
                      {STATUS_LABEL[d.status]}
                    </span>
                    {d.status === "cleaned" && (d.row_count_clean ?? 0) > 0 && (
                      <Link to={`/dashboard/${d.id}`} className="text-[hsl(var(--primary))] hover:underline">
                        View dashboard
                      </Link>
                    )}
                    {d.status === "mapping_pending" && (
                      <Link to={`/datasets/${d.id}/mapping`} className="text-[hsl(var(--primary))] hover:underline">
                        Review mapping
                      </Link>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
          <div className="mt-4">
            <Button variant="outline" onClick={refreshDatasets}>
              Refresh
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
