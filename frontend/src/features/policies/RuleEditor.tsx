import { Button } from "../../components/ui/button";
import { FormField } from "../../components/ui/form";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import type { PolicyRule } from "../../lib/api";

type RuleEditorProps = {
  value: PolicyRule[];
  onChange: (rules: PolicyRule[]) => void;
};

const emptyRule = (): PolicyRule => ({
  category_name: "",
  vendor_name: "",
  per_category_cap: null,
  max_per_trip: null,
  receipt_required_above: null,
});

function toNumberOrNull(value: string) {
  if (value.trim() === "") return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

export function RuleEditor({ value, onChange }: RuleEditorProps) {
  const updateRule = (index: number, key: keyof PolicyRule, rawValue: string) => {
    const numericKeys: Array<keyof PolicyRule> = ["per_category_cap", "max_per_trip", "max_per_day", "receipt_required_above"];
    const nextValue = numericKeys.includes(key) ? toNumberOrNull(rawValue) : rawValue;
    onChange(value.map((rule, ruleIndex) => (ruleIndex === index ? { ...rule, [key]: nextValue } : rule)));
  };

  return (
    <fieldset className="space-y-3 rounded-lg border border-slate-200 p-4 dark:border-slate-700">
      <legend className="px-1 text-sm font-semibold text-slate-800 dark:text-slate-100">Rules</legend>
      <p className="text-sm text-slate-600 dark:text-slate-300">
        Add category or vendor limits and the amount at which a receipt becomes required.
      </p>

      {value.map((rule, index) => (
        <div key={rule.id ?? `new-rule-${index}`} className="grid gap-3 rounded-md bg-slate-50 p-3 md:grid-cols-2 dark:bg-slate-800/60">
          <FormField>
            <Label htmlFor={`rule-category-${index}`}>Category</Label>
            <Input
              id={`rule-category-${index}`}
              value={rule.category_name ?? rule.category_id ?? ""}
              onChange={(event) => updateRule(index, "category_name", event.target.value)}
              placeholder="e.g. Travel"
            />
          </FormField>
          <FormField>
            <Label htmlFor={`rule-vendor-${index}`}>Vendor</Label>
            <Input
              id={`rule-vendor-${index}`}
              value={rule.vendor_name ?? rule.vendor_id ?? ""}
              onChange={(event) => updateRule(index, "vendor_name", event.target.value)}
              placeholder="Optional vendor"
            />
          </FormField>
          <FormField>
            <Label htmlFor={`rule-cap-${index}`}>Category cap</Label>
            <Input
              id={`rule-cap-${index}`}
              min="0"
              step="0.01"
              type="number"
              value={rule.per_category_cap ?? ""}
              onChange={(event) => updateRule(index, "per_category_cap", event.target.value)}
              placeholder="0.00"
            />
          </FormField>
          <FormField>
            <Label htmlFor={`rule-trip-cap-${index}`}>Trip cap</Label>
            <Input
              id={`rule-trip-cap-${index}`}
              min="0"
              step="0.01"
              type="number"
              value={rule.max_per_trip ?? ""}
              onChange={(event) => updateRule(index, "max_per_trip", event.target.value)}
              placeholder="0.00"
            />
          </FormField>
          <FormField>
            <Label htmlFor={`rule-day-cap-${index}`}>Daily cap</Label>
            <Input
              id={`rule-day-cap-${index}`}
              min="0"
              step="0.01"
              type="number"
              value={rule.max_per_day ?? ""}
              onChange={(event) => updateRule(index, "max_per_day", event.target.value)}
              placeholder="0.00"
            />
          </FormField>
          <FormField>
            <Label htmlFor={`rule-receipt-${index}`}>Receipt required above</Label>
            <Input
              id={`rule-receipt-${index}`}
              min="0"
              step="0.01"
              type="number"
              value={rule.receipt_required_above ?? ""}
              onChange={(event) => updateRule(index, "receipt_required_above", event.target.value)}
              placeholder="0.00"
            />
          </FormField>
          <div className="flex items-end justify-end">
            <Button
              aria-label={`Remove rule ${index + 1}`}
              onClick={() => onChange(value.filter((_, ruleIndex) => ruleIndex !== index))}
              variant="ghost"
            >
              Remove rule
            </Button>
          </div>
        </div>
      ))}

      <Button onClick={() => onChange([...value, emptyRule()])} type="button" variant="outline">
        Add rule
      </Button>
    </fieldset>
  );
}
