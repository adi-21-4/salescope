import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  confirmMapping,
  previewDataset,
  type ColumnDetection,
  type ConfirmMappingResult,
  type MappingRole,
} from "@/api/datasets";
import ColumnMappingTable from "@/components/ColumnMappingTable";
import StatusValueFilter, { defaultIncludedStatusValues } from "@/components/StatusValueFilter";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const REQUIRED_ROLES: MappingRole[] = ["date"];
// Exactly one of these is required -- "price" (per-unit) or "line_total" (an
// already-computed total for that row, e.g. "Net Amount"). Picking the wrong
// one for a file that has both silently multiplies revenue by quantity twice.
const PRICE_ROLES: MappingRole[] = ["price", "line_total"];

export default function MappingReview() {
  const { datasetId } = useParams<{ datasetId: string }>();
  const navigate = useNavigate();

  const [columns, setColumns] = useState<ColumnDetection[]>([]);
  const [mapping, setMapping] = useState<Record<string, MappingRole>>({});
  const [includedStatusValues, setIncludedStatusValues] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ConfirmMappingResult | null>(null);

  useEffect(() => {
    if (!datasetId) return;
    previewDataset(datasetId)
      .then((preview) => {
        setColumns(preview.columns);
        const initial: Record<string, MappingRole> = {};
        for (const col of preview.columns) {
          initial[col.column] = col.detected_role ?? "ignore";
        }
        setMapping(initial);

        const statusCol = preview.columns.find((c) => c.detected_role === "status");
        if (statusCol) setIncludedStatusValues(defaultIncludedStatusValues(statusCol.distinct_values));
      })
      .catch(() => setError("Could not load column preview"))
      .finally(() => setIsLoading(false));
  }, [datasetId]);

  const mappedRoles = Object.values(mapping);
  const missingRequired = REQUIRED_ROLES.filter((role) => !mappedRoles.includes(role));
  const hasPriceRole = PRICE_ROLES.some((role) => mappedRoles.includes(role));
  const hasBothPriceRoles = PRICE_ROLES.every((role) => mappedRoles.includes(role));
  const statusColumnName = Object.entries(mapping).find(([, role]) => role === "status")?.[0];
  const statusColumn = statusColumnName ? columns.find((c) => c.column === statusColumnName) : undefined;

  function handleMappingChange(column: string, role: MappingRole) {
    setMapping((prev) => {
      const next = { ...prev, [column]: role };
      // Every role except "ignore" can only point to one column -- mapping.ts's
      // cleaner silently keeps only the last-assigned column for a duplicated
      // role, which loses data with zero warning. Demote any previous holder.
      if (role !== "ignore") {
        for (const key of Object.keys(next)) {
          if (key !== column && next[key] === role) next[key] = "ignore";
        }
      }
      return next;
    });
    if (role === "status") {
      const detected = columns.find((c) => c.column === column);
      setIncludedStatusValues(defaultIncludedStatusValues(detected?.distinct_values ?? []));
    }
  }

  async function handleConfirm() {
    if (!datasetId) return;
    setError(null);
    setIsSubmitting(true);
    try {
      const res = await confirmMapping(
        datasetId,
        mapping,
        statusColumnName ? includedStatusValues : null
      );
      setResult(res);
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Could not confirm mapping");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isLoading) return <p>Loading column preview…</p>;

  if (result) {
    return (
      <Card className="mx-auto max-w-xl">
        <CardHeader>
          <CardTitle>Data cleaned</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <p>{result.rows_clean} rows are ready in your dashboard.</p>
          {result.invalid_date_count > 0 && (
            <p className="text-[hsl(var(--muted-foreground))]">
              {result.invalid_date_count} rows had invalid dates and were excluded.
            </p>
          )}
          {result.excluded_by_status_count > 0 && (
            <p className="text-[hsl(var(--muted-foreground))]">
              {result.excluded_by_status_count} rows were excluded because their status wasn't marked as
              completed.
            </p>
          )}
          {result.incomplete_count > 0 && (
            <p className="text-[hsl(var(--muted-foreground))]">
              {result.incomplete_count} rows were missing quantity/price and are flagged incomplete.
            </p>
          )}
          {result.duplicate_count > 0 && (
            <p className="text-[hsl(var(--muted-foreground))]">
              {result.duplicate_count} duplicate rows within this file were skipped.
            </p>
          )}
          {result.already_existed_count > 0 && (
            <p className="text-[hsl(var(--muted-foreground))]">
              {result.already_existed_count} rows matched sales you'd already uploaded before, so they
              weren't added again.
            </p>
          )}
          {result.rows_clean === 0 && result.already_existed_count > 0 && (
            <p className="rounded-md bg-[hsl(var(--muted))] p-3 text-[hsl(var(--foreground))]">
              This entire file's data is already in your account — nothing new to add. If you meant to
              upload different data, check you picked the right file.
            </p>
          )}
          <Button
            className="mt-4"
            onClick={() => navigate(`/dashboard/${datasetId}`)}
            disabled={result.rows_clean === 0}
          >
            View dashboard
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Review column mapping</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="mb-4 text-sm text-[hsl(var(--muted-foreground))]">
            We auto-detected what each column represents. Correct anything that looks wrong before we
            build your dashboard — nothing is saved until you confirm.
          </p>
          <ColumnMappingTable columns={columns} mapping={mapping} onChange={handleMappingChange} />
          <p className="mt-2 text-xs text-[hsl(var(--muted-foreground))]">
            If your file has both a per-unit price and a total/amount column, map the <strong>total</strong>{" "}
            column as "Amount (total for this row)" — not "Price (per unit)" — otherwise revenue gets
            multiplied by quantity twice.
          </p>
          {hasBothPriceRoles && (
            <p className="mt-2 text-sm text-[hsl(var(--destructive))]">
              You've mapped both a Price and an Amount column — only the Amount (total) column will be
              used; the Price column will be ignored. Set one of them to "Ignore" if that's not what you
              want.
            </p>
          )}
          {statusColumn && (
            <StatusValueFilter
              distinctValues={statusColumn.distinct_values}
              included={includedStatusValues}
              onChange={setIncludedStatusValues}
            />
          )}
          {(missingRequired.length > 0 || !hasPriceRole) && (
            <p className="mt-4 text-sm text-[hsl(var(--destructive))]">
              Please map a column to: {[...missingRequired, ...(hasPriceRole ? [] : ["Price or Amount"])].join(", ")}
            </p>
          )}
          {!Object.values(mapping).includes("quantity") && (
            <p className="mt-4 text-sm text-[hsl(var(--muted-foreground))]">
              No quantity column mapped — each row will be treated as 1 unit (fine for services/bookings
              where every row is one sale).
            </p>
          )}
          {error && <p className="mt-4 text-sm text-[hsl(var(--destructive))]">{error}</p>}
          <Button
            className="mt-4"
            onClick={handleConfirm}
            disabled={isSubmitting || missingRequired.length > 0 || !hasPriceRole}
          >

            {isSubmitting ? "Cleaning data…" : "Confirm & build dashboard"}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
