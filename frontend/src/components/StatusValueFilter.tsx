const LIKELY_EXCLUDED_PATTERN = /cancel|pending|refund|void|fail|declin|return|unpaid/i;

export function defaultIncludedStatusValues(distinctValues: string[]): string[] {
  return distinctValues.filter((v) => !LIKELY_EXCLUDED_PATTERN.test(v));
}

interface Props {
  distinctValues: string[];
  included: string[];
  onChange: (included: string[]) => void;
}

export default function StatusValueFilter({ distinctValues, included, onChange }: Props) {
  function toggle(value: string) {
    if (included.includes(value)) {
      onChange(included.filter((v) => v !== value));
    } else {
      onChange([...included, value]);
    }
  }

  return (
    <div className="mt-3 rounded-md border border-[hsl(var(--border))] p-3">
      <p className="mb-2 text-sm font-medium">Which statuses count as a completed sale?</p>
      <p className="mb-3 text-xs text-[hsl(var(--muted-foreground))]">
        Unchecked values (e.g. Cancelled, Pending, Refunded) are excluded from revenue and all charts.
      </p>
      <div className="flex flex-wrap gap-3">
        {distinctValues.map((value) => (
          <label key={value} className="flex items-center gap-1.5 text-sm">
            <input type="checkbox" checked={included.includes(value)} onChange={() => toggle(value)} />
            {value}
          </label>
        ))}
      </div>
    </div>
  );
}
