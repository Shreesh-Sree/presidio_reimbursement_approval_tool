import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "../../components/ui/button";
import { LoadingState } from "../../components/ui/loading-state";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "../../components/ui/dialog";
import { ConfirmDialog } from "../../components/ui/confirm-dialog";
import { Form, FormField } from "../../components/ui/form";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Select } from "../../components/ui/select";
import { categoriesApi, type Category, type CategoryInput } from "../../lib/api";

type CategoryFormState = {
  code: string;
  name: string;
  parent_id: string;
  description: string;
  max_per_day: string;
  max_per_trip: string;
  receipt_required_above: string;
};

const emptyForm: CategoryFormState = {
  code: "",
  name: "",
  parent_id: "",
  description: "",
  max_per_day: "",
  max_per_trip: "",
  receipt_required_above: "",
};

function flattenCategories(categories: Category[]): Category[] {
  return categories.flatMap((category) => [
    { ...category, children: undefined },
    ...(category.children ? flattenCategories(category.children) : []),
  ]);
}

function categoryTree(categories: Category[]) {
  const flat = flattenCategories(categories);
  const unique = Array.from(new Map(flat.map((category) => [category.id, { ...category, children: [] as Category[] }])).values());
  const byId = new Map(unique.map((category) => [category.id, category]));
  const roots: Category[] = [];

  unique.forEach((category) => {
    if (category.parent_id && byId.has(category.parent_id)) byId.get(category.parent_id)?.children?.push(category);
    else roots.push(category);
  });

  return roots;
}

function CategoryBranch({ category, depth, onEdit, onDelete }: { category: Category; depth: number; onEdit: (category: Category) => void; onDelete: (category: Category) => void }) {
  return (
    <li className="relative space-y-2" role="treeitem">
      <div className={`relative flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:flex-row sm:items-center sm:justify-between dark:border-slate-800 dark:bg-slate-900 ${depth ? "before:absolute before:-left-5 before:top-1/2 before:h-px before:w-5 before:bg-slate-300 dark:before:bg-slate-700" : ""}`}>
        <div>
          <p className="font-semibold text-slate-950 dark:text-white">{category.name}</p>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            {category.code}{category.description ? ` · ${category.description}` : ""}
            {(category.max_per_day != null || category.max_amount != null) && (
              <span className="ml-2 inline-flex items-center rounded-md bg-orange-100 px-2 py-0.5 text-xs font-medium text-orange-800 dark:bg-orange-950 dark:text-orange-300">
                Max ${category.max_per_day ?? category.max_amount}/day
              </span>
            )}
          </p>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => onEdit(category)} variant="outline">Edit</Button>
          <Button onClick={() => onDelete(category)} variant="ghost">Delete</Button>
        </div>
      </div>
      {category.children && category.children.length > 0 && (
        <ul className="relative ml-5 space-y-2 border-l border-slate-300 pl-5 dark:border-slate-700" role="group">
          {category.children.map((child) => <CategoryBranch category={child} depth={depth + 1} key={child.id} onDelete={onDelete} onEdit={onEdit} />)}
        </ul>
      )}
    </li>
  );
}

export function CategoriesPage() {
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingCategory, setEditingCategory] = useState<Category | null>(null);
  const [deletingCategory, setDeletingCategory] = useState<Category | null>(null);
  const [showArchived, setShowArchived] = useState(false);
  const [values, setValues] = useState<CategoryFormState>(emptyForm);
  const categories = useQuery({ queryKey: ["categories", showArchived], queryFn: () => showArchived ? categoriesApi.listWithArchived() : categoriesApi.list() });
  const activeCategories = useMemo(() => (categories.data ?? []).filter((category) => !category.is_deleted), [categories.data]);
  const archivedCategories = useMemo(() => (categories.data ?? []).filter((category) => category.is_deleted), [categories.data]);
  const allCategories = useMemo(() => flattenCategories(activeCategories), [activeCategories]);

  useEffect(() => {
    if (!dialogOpen) return;
    setValues(editingCategory ? {
      code: editingCategory.code,
      name: editingCategory.name,
      parent_id: editingCategory.parent_id ?? "",
      description: editingCategory.description ?? "",
      max_per_day: editingCategory.max_per_day != null ? String(editingCategory.max_per_day) : (editingCategory.max_amount != null ? String(editingCategory.max_amount) : ""),
      max_per_trip: editingCategory.max_per_trip != null ? String(editingCategory.max_per_trip) : "",
      receipt_required_above: editingCategory.receipt_required_above != null ? String(editingCategory.receipt_required_above) : "",
    } : emptyForm);
  }, [dialogOpen, editingCategory]);

  const saveCategory = useMutation({
    mutationFn: () => {
      const input: CategoryInput = {
        code: values.code,
        name: values.name,
        parent_id: values.parent_id || null,
        description: values.description || null,
        max_per_day: values.max_per_day ? Number(values.max_per_day) : undefined,
        max_per_trip: values.max_per_trip ? Number(values.max_per_trip) : undefined,
        receipt_required_above: values.receipt_required_above ? Number(values.receipt_required_above) : undefined,
        max_amount: values.max_per_day ? Number(values.max_per_day) : undefined,
      };
      return editingCategory ? categoriesApi.update(editingCategory.id, input) : categoriesApi.create(input);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["categories"] });
      setDialogOpen(false);
    },
  });

  const deleteCategory = useMutation({
    mutationFn: categoriesApi.remove,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["categories"] }),
  });

  const openCreate = () => {
    setEditingCategory(null);
    setDialogOpen(true);
  };

  const openEdit = (category: Category) => {
    setEditingCategory(category);
    setDialogOpen(true);
  };

  return (
    <main className="mx-auto w-full max-w-5xl space-y-6 p-4 sm:p-6">
      <header className="flex flex-col gap-4 border-b border-slate-200 pb-5 sm:flex-row sm:items-center sm:justify-between dark:border-slate-800">
        <div>
          <p className="text-sm font-medium text-orange-600 dark:text-orange-400">Policy management</p>
          <h1 className="mt-1 text-2xl font-semibold text-slate-950 dark:text-white">Expense categories</h1>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Organize categories with mandatory policy rules for expense compliance.</p>
        </div>
        <div className="flex gap-2"><Button onClick={() => setShowArchived((value) => !value)} variant="outline">{showArchived ? "Hide archived" : "Archived categories"}</Button><Button onClick={openCreate}>New category</Button></div>
      </header>

      {categories.isLoading && <LoadingState label="Loading categories" />}
      {categories.isError && <p className="rounded-md bg-orange-50 p-3 text-sm text-orange-700 dark:bg-orange-950/40 dark:text-orange-200">Unable to load categories.</p>}
      {categories.data?.length === 0 && <p className="rounded-lg border border-dashed border-slate-300 p-8 text-center text-sm text-slate-600 dark:border-slate-700 dark:text-slate-300">No categories have been created.</p>}
      <ul className="space-y-2" role="tree">
        {categoryTree(activeCategories).map((category) => (
          <CategoryBranch
            category={category}
            depth={0}
            key={category.id}
            onDelete={setDeletingCategory}
            onEdit={openEdit}
          />
        ))}
      </ul>
      {showArchived && (
        <section className="overflow-hidden rounded-2xl border border-amber-400/30 bg-amber-50/60 dark:border-amber-300/20 dark:bg-amber-950/15">
          <header className="border-b border-amber-400/25 px-5 py-4 dark:border-amber-300/15">
            <p className="text-sm font-bold text-amber-900 dark:text-amber-100">Archived categories</p>
            <p className="mt-1 text-sm text-amber-800/80 dark:text-amber-100/70">Archived records are hidden from reports. Restore one to use its code again.</p>
          </header>
          <div className="divide-y divide-amber-400/20 dark:divide-amber-300/15">
            {archivedCategories.length ? archivedCategories.map((category) => (
              <article className="flex flex-col gap-4 px-5 py-4 sm:flex-row sm:items-center sm:justify-between" key={`archived-${category.id}`}>
                <div><p className="font-semibold text-[#202020] dark:text-[#fcfcfc]">{category.name}</p><p className="mt-1 text-sm text-[#646464] dark:text-white/65">Code: {category.code}{category.description ? ` · ${category.description}` : ""}</p></div>
                <div className="flex flex-wrap gap-2"><Button onClick={() => categoriesApi.restore(category.id).then(() => queryClient.invalidateQueries({ queryKey: ["categories"] }))} variant="outline">Restore category</Button><Button onClick={() => categoriesApi.permanentlyDelete(category.id).then(() => queryClient.invalidateQueries({ queryKey: ["categories"] }))} variant="destructive">Delete permanently</Button></div>
              </article>
            )) : <p className="px-5 py-6 text-sm text-[#646464] dark:text-white/65">There are no archived categories.</p>}
          </div>
        </section>
      )}

      <Dialog onOpenChange={setDialogOpen} open={dialogOpen}>
        <DialogContent>
          <DialogTitle>{editingCategory ? "Edit category" : "New category"}</DialogTitle>
          <DialogDescription>Every category must have policy rules defined to govern employee claims.</DialogDescription>
          <Form
            className="mt-5 space-y-4"
            onSubmit={(event) => {
              event.preventDefault();
              saveCategory.mutate();
            }}
          >
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField>
                <Label htmlFor="category-code">Code</Label>
                <Input id="category-code" onChange={(event) => setValues((current) => ({ ...current, code: event.target.value }))} required value={values.code} />
              </FormField>
              <FormField>
                <Label htmlFor="category-name">Name</Label>
                <Input id="category-name" onChange={(event) => setValues((current) => ({ ...current, name: event.target.value }))} required value={values.name} />
              </FormField>
            </div>
            <FormField>
              <Label htmlFor="category-parent">Parent category</Label>
              <Select id="category-parent" onChange={(event) => setValues((current) => ({ ...current, parent_id: event.target.value }))} value={values.parent_id}>
                <option value="">No parent (top-level)</option>
                {allCategories.filter((category) => category.id !== editingCategory?.id).map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
              </Select>
            </FormField>
            <FormField>
              <Label htmlFor="category-description">Description</Label>
              <Input id="category-description" onChange={(event) => setValues((current) => ({ ...current, description: event.target.value }))} value={values.description} />
            </FormField>

            <div className="rounded-xl border border-orange-200 bg-orange-50/60 p-4 dark:border-orange-900/40 dark:bg-orange-950/20">
              <p className="text-xs font-bold uppercase tracking-wider text-orange-700 dark:text-orange-300">Mandatory Category Policy Rules</p>
              <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">Rules defined here directly enforce limits during employee claim submission.</p>
              <div className="mt-3 grid gap-3 sm:grid-cols-3">
                <FormField>
                  <Label htmlFor="category-max-day">Daily Limit ($)</Label>
                  <Input id="category-max-day" onChange={(e) => setValues((c) => ({ ...c, max_per_day: e.target.value }))} placeholder="75.00" required={!editingCategory} step="0.01" type="number" value={values.max_per_day} />
                </FormField>
                <FormField>
                  <Label htmlFor="category-max-trip">Trip Limit ($)</Label>
                  <Input id="category-max-trip" onChange={(e) => setValues((c) => ({ ...c, max_per_trip: e.target.value }))} placeholder="500.00" step="0.01" type="number" value={values.max_per_trip} />
                </FormField>
                <FormField>
                  <Label htmlFor="category-receipt-above">Receipt Req. Above ($)</Label>
                  <Input id="category-receipt-above" onChange={(e) => setValues((c) => ({ ...c, receipt_required_above: e.target.value }))} placeholder="25.00" step="0.01" type="number" value={values.receipt_required_above} />
                </FormField>
              </div>
            </div>

            {saveCategory.isError && <p className="text-sm text-orange-600">Unable to save this category. Ensure policy rules are specified.</p>}
            <div className="flex flex-col-reverse justify-end gap-2 pt-2 sm:flex-row">
              <Button onClick={() => setDialogOpen(false)} variant="outline">Cancel</Button>
              <Button disabled={saveCategory.isPending} type="submit">{saveCategory.isPending ? "Saving…" : "Save category"}</Button>
            </div>
          </Form>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        description={`Delete ${deletingCategory?.name ?? "this category"}? This cannot be undone.`}
        onConfirm={() => deletingCategory && deleteCategory.mutate(deletingCategory.id, { onSuccess: () => setDeletingCategory(null) })}
        onOpenChange={(open) => !open && setDeletingCategory(null)}
        open={Boolean(deletingCategory)}
        title="Delete category"
      />
    </main>
  );
}
