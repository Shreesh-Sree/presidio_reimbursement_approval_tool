import { Button } from "../../components/ui/button";
import { FormField } from "../../components/ui/form";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Select } from "../../components/ui/select";
import { AuthenticatedAttachmentLink } from "../../components/AuthenticatedAttachmentLink";
import type { Category, ReportLineItem, Vendor } from "../../lib/api";
import { ReceiptUpload } from "./ReceiptUpload";

type LineItemRowProps = {
  item: ReportLineItem;
  index: number;
  categories: Category[];
  vendors: Vendor[];
  selectionsLoading?: boolean;
  disabled?: boolean;
  isSaving?: boolean;
  onDelete: (item: ReportLineItem) => void;
  onSave: (item: ReportLineItem) => void;
  onUpdate: (item: ReportLineItem) => void;
  onReceiptUploaded?: () => void;
};

function amountFromInput(value: string) {
  if (value.trim() === "") return 0;
  const amount = Number(value);
  return Number.isFinite(amount) ? amount : 0;
}

export function LineItemRow({
  item,
  index,
  categories,
  vendors,
  selectionsLoading = false,
  disabled = false,
  isSaving = false,
  onDelete,
  onSave,
  onUpdate,
  onReceiptUploaded,
}: LineItemRowProps) {
  const receiptUrl = item.receipt?.url ?? item.receipt_url;
  const violationReason = item.violation_reason ?? item.policy_violation_reason;
  const isNewItem = item.id.startsWith("new-");
  const canSave = Boolean(item.category_id && item.description.trim() && item.expense_date && Number(item.amount) > 0);
  const update = (changes: Partial<ReportLineItem>) => onUpdate({ ...item, ...changes });

  return (
    <article className="space-y-4 rounded-lg border border-slate-200 p-4 dark:border-slate-800">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-medium text-slate-950 dark:text-white">Line item {index + 1}</h3>
        <div className="flex gap-2">
          <Button disabled={disabled || isSaving || !canSave} onClick={() => onSave(item)} variant="outline">
            {isSaving ? "Saving…" : "Save item"}
          </Button>
          <Button aria-label={`Delete line item ${index + 1}`} disabled={disabled || isSaving} onClick={() => onDelete(item)} variant="ghost">
            Delete
          </Button>
        </div>
      </div>

      {!disabled && !canSave && (
        <p className="text-sm text-amber-700 dark:text-amber-300">Choose a category and complete the description, date, and positive amount before saving.</p>
      )}

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
          <Select
            disabled={disabled || selectionsLoading}
            id={`item-category-${index}`}
            onChange={(event) => {
              const category = categories.find((candidate) => candidate.id === event.target.value);
              update({ category_id: category?.id, category_name: category?.name ?? "" });
            }}
            required
            value={item.category_id ?? ""}
          >
            <option value="">{selectionsLoading ? "Loading categories…" : "Choose a category"}</option>
            {categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
          </Select>
        </FormField>
      </div>

      {(() => {
        const selectedCategory = categories.find((c) => c.id === item.category_id);
        if (!selectedCategory) return null;

        const maxLimit = selectedCategory.max_per_day ?? selectedCategory.max_amount;
        const receiptThreshold = selectedCategory.receipt_required_above ?? (selectedCategory.receipt_required ? 0 : null);
        const isExceedingLimit = maxLimit != null && item.amount > maxLimit;
        const isReceiptRequired = receiptThreshold != null && item.amount > receiptThreshold && !item.receipt_url && !item.receipt;

        return (
          <div className="space-y-2">
            <div className="rounded-md border border-blue-200 bg-blue-50/70 p-3 text-xs text-blue-950 dark:border-blue-900/40 dark:bg-blue-950/30 dark:text-blue-200">
              <span className="font-bold">📌 Policy Rule for {selectedCategory.name}:</span>{" "}
              {maxLimit != null ? `Daily Limit: $${maxLimit}.` : "No daily cap."}{" "}
              {selectedCategory.max_per_trip != null ? `Trip Limit: $${selectedCategory.max_per_trip}.` : ""}{" "}
              {receiptThreshold != null ? `Receipt required above $${receiptThreshold}.` : "Receipt optional."}
            </div>
            {isExceedingLimit && (
              <p className="rounded-md border border-red-200 bg-red-50 p-2.5 text-xs font-medium text-red-800 dark:border-red-900/40 dark:bg-red-950/40 dark:text-red-200">
                ⚠️ Amount (${item.amount}) exceeds the category daily limit of ${maxLimit}.
              </p>
            )}
            {isReceiptRequired && (
              <p className="rounded-md border border-amber-200 bg-amber-50 p-2.5 text-xs font-medium text-amber-800 dark:border-amber-900/40 dark:bg-amber-950/40 dark:text-amber-200">
                📄 Attachment required: Amount exceeds ${receiptThreshold} threshold for {selectedCategory.name}.
              </p>
            )}
          </div>
        );
      })()}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <FormField>
          <Label htmlFor={`item-vendor-${index}`}>Saved vendor (optional)</Label>
          <Select
            disabled={disabled || selectionsLoading}
            id={`item-vendor-${index}`}
            onChange={(event) => {
              const vendor = vendors.find((candidate) => candidate.id === event.target.value);
              update({
                vendor_id: vendor?.id,
                vendor_name: vendor?.name ?? "",
                merchant_name: vendor ? null : item.merchant_name ?? item.vendor_name ?? "",
              });
            }}
            value={item.vendor_id ?? ""}
          >
            <option value="">{selectionsLoading ? "Loading vendors…" : "Not in vendor list"}</option>
            {vendors.map((vendor) => <option key={vendor.id} value={vendor.id}>{vendor.name}</option>)}
          </Select>
        </FormField>
        {!item.vendor_id && (
          <FormField>
            <Label htmlFor={`item-merchant-${index}`}>Merchant name</Label>
            <Input
              disabled={disabled}
              id={`item-merchant-${index}`}
              onChange={(event) => update({ merchant_name: event.target.value, vendor_name: event.target.value })}
              placeholder="e.g. City Taxi"
              value={item.merchant_name ?? item.vendor_name ?? ""}
            />
          </FormField>
        )}
        <FormField>
          <Label htmlFor={`item-date-${index}`}>Expense date for line item {index + 1}</Label>
          <Input
            disabled={disabled}
            id={`item-date-${index}`}
            onChange={(event) => update({ expense_date: event.target.value })}
            required
            type="date"
            value={item.expense_date?.slice(0, 10) ?? ""}
          />
        </FormField>
        <FormField>
          <Label htmlFor={`item-currency-${index}`}>Currency</Label>
          <Input
            disabled={disabled}
            id={`item-currency-${index}`}
            maxLength={3}
            onChange={(event) => update({ currency: event.target.value.toUpperCase() })}
            placeholder="INR"
            value={item.currency ?? item.currency_code ?? ""}
          />
        </FormField>
      </div>

      {violationReason && (
        <p className="rounded-md bg-orange-50 p-3 text-sm text-orange-800 dark:bg-orange-950/40 dark:text-orange-100">
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
            onUploadComplete={(receipt) => {
              update({ receipt, receipt_url: receipt.url });
              onReceiptUploaded?.();
            }}
          />
          {receiptUrl && (
            <AuthenticatedAttachmentLink className="h-auto min-h-0 px-0 py-0 text-sm font-medium text-orange-600 underline underline-offset-2 hover:bg-transparent dark:text-orange-300" url={receiptUrl}>
              View receipt{item.receipt?.file_name ? ` (${item.receipt.file_name})` : ""}
            </AuthenticatedAttachmentLink>
          )}
        </div>
      )}
    </article>
  );
}
