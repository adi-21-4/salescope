import type { ColumnDetection, MappingRole } from "@/api/datasets";

const ROLE_OPTIONS: { value: MappingRole; label: string }[] = [
  { value: "ignore", label: "Ignore" },
  { value: "date", label: "Date" },
  { value: "product", label: "Product" },
  { value: "quantity", label: "Quantity" },
  { value: "price", label: "Price (per unit)" },
  { value: "line_total", label: "Amount (total for this row)" },
  { value: "category", label: "Category" },
  { value: "status", label: "Status" },
  { value: "location", label: "Location / Agent" },
  { value: "payment_method", label: "Payment Method" },
];

interface Props {
  columns: ColumnDetection[];
  mapping: Record<string, MappingRole>;
  onChange: (column: string, role: MappingRole) => void;
}

export default function ColumnMappingTable({ columns, mapping, onChange }: Props) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-[hsl(var(--border))] text-[hsl(var(--muted-foreground))]">
            <th className="py-2 pr-4">Column</th>
            <th className="py-2 pr-4">Sample values</th>
            <th className="py-2 pr-4">Detected as</th>
            <th className="py-2 pr-4">Role</th>
          </tr>
        </thead>
        <tbody>
          {columns.map((col) => {
            const otherCandidates = col.candidates.filter((c) => c.role !== col.detected_role);
            return (
              <tr key={col.column} className="border-b border-[hsl(var(--border))]">
                <td className="py-3 pr-4 font-medium">{col.column}</td>
                <td className="py-3 pr-4 text-[hsl(var(--muted-foreground))]">
                  {col.sample_values.slice(0, 3).join(", ") || "—"}
                </td>
                <td className="py-3 pr-4">
                  {col.detected_role ? (
                    <div>
                      <span className="rounded-full bg-[hsl(var(--muted))] px-2 py-1 text-xs capitalize">
                        {col.detected_role} · {Math.round(col.confidence * 100)}%
                      </span>
                      {otherCandidates.length > 0 && (
                        <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
                          Also could be: {otherCandidates.map((c) => c.role).join(", ")}
                        </p>
                      )}
                    </div>
                  ) : (
                    <span className="text-xs text-[hsl(var(--muted-foreground))]">Unmapped — please choose</span>
                  )}
                </td>
                <td className="py-3 pr-4">
                  <select
                    value={mapping[col.column] ?? "ignore"}
                    onChange={(e) => onChange(col.column, e.target.value as MappingRole)}
                    className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--card))] px-2 py-1 text-sm text-[hsl(var(--card-foreground))]"
                  >
                    {ROLE_OPTIONS.map((opt) => (
                      <option
                        key={opt.value}
                        value={opt.value}
                        className="bg-[hsl(var(--card))] text-[hsl(var(--card-foreground))]"
                      >
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
