import { Button } from "../../components/ui/button";
import { FormField } from "../../components/ui/form";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import type { ReportLineItem } from "../../lib/api";
import { ReceiptUpload } from "./ReceiptUpload";

type LineItemRowProps = {
  item: ReportLineItem;
  index: number;
  disabled?: boolean;
  isSaving?: boolean;
  onDelete: (item: ReportLineItem) => void;
  onSave: (item: ReportLineItem) => void;
  onUpdate: (item: ReportLineItem) => void;
};

function amountFromInput(value: string) {
  if (value.trim() === "") return 0;
  const amount = Number(value);
  return Number.isFinite(amount) ? amount : 0;
}

export function LineItemRow({ item, index, disabled = false, isSaving = false, onDelete, onSave, onUpdate }: LineItemRowProps) {
  const receiptUrl = item.receipt?.url ?? item.receipt_url;
  const violationReason = item.violation_reason ?? item.policy_violation_reason;
  const isNewItem = item.id.startsWith("new-");
  const update = (changes: Partial<ReportLineItem>) => onUpdate({ ...item, ...changes });

  return (
    <article className="space-y-4 rounded-lg border border-slate-200 p-4 dark:border-slate-800">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-medium text-slate-950 dark:text-white">Line item {index + 1}</h3>
        <div className="flex gap-2">
          <Button disabled={disabled || isSaving} onClick={() => onSave(item)} variant="outline">
            {isSaving ? "Saving…" : "Save item"}
          </Button>
          <Button aria-label={`Delete line item ${index + 1}`} disabled={disabled || isSaving} onClick={() => onDelete(item)} variant="ghost">
            Delete
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <FormField className="xl:col-span-2">
          <Label htmlFor={`item-description-${index}`}>Description for line item {index + 1}</Label>
          <Input
            disabled={disabled}
            id={`item-description-${index}`}
            onChange={(event) => update({ description: event.target.value })}
            value={item.description}
          />
        </FormField>
        <FormField>
          <Label htmlFor={`item-amount-${index}`}>Amount for line item {index + 1}</Label>
          <Input
            disabled={disabled}
            id={`item-amount-${index}`}
            min="0"
            onChange={(event) => update({ amount: amountFromInput(event.target.value) })}
            step="0.01"
            type="number"
            value={item.amount || ""}
          />
        </FormField>
        <FormField>
          <Label htmlFor={`item-category-${index}`}>Category for line item {index + 1}</Label>
          <Input
            disabled={disabled}
            id={`item-category-${index}`}
            onChange={(event) => update({ category_name: event.target.value })}
            value={item.category_name ?? ""}
          />
        </FormField>
        <FormField>
          <Label htmlFor={`item-vendor-${index}`}>Vendor for line item {index + 1}</Label>
          <Input
            disabled={disabled}
            id={`item-vendor-${index}`}
            onChange={(event) => update({ vendor_name: event.target.value })}
            value={item.vendor_name ?? ""}
          />
        </FormField>
        <FormField>
          <Label htmlFor={`item-date-${index}`}>Expense date for line item {index + 1}</Label>
          <Input
            disabled={disabled}
            id={`item-date-${index}`}
            onChange={(event) => update({ expense_date: event.target.value })}
            type="date"
            value={item.expense_date?.slice(0, 10) ?? ""}
          />
        </FormField>
      </div>

      {violationReason && (
        <p className="rounded-md bg-rose-50 p-3 text-sm text-rose-800 dark:bg-rose-950/40 dark:text-rose-100">
          <span className="font-semibold">Policy violation:</span> {violationReason}
        </p>
      )}

      {isNewItem ? (
        <p className="text-sm text-slate-600 dark:text-slate-300">Save this line item before attaching a receipt.</p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 sm:items-end">
          <ReceiptUpload
            disabled={disabled}
            itemId={item.id}
            onUploadComplete={(receipt) => update({ receipt, receipt_url: receipt.url })}
          />
          {receiptUrl && (
            <a className="text-sm font-medium text-indigo-600 underline underline-offset-2 dark:text-indigo-300" href={receiptUrl} rel="noreferrer" target="_blank">
              View receipt
            </a>
          )}
        </div>
      )}
    </article>
  );
}
