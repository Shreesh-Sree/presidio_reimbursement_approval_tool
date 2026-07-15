import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "../../components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "../../components/ui/dialog";
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
};

const emptyForm: CategoryFormState = { code: "", name: "", parent_id: "", description: "" };

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
    <li className="space-y-2" role="treeitem">
      <div className="flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-3 sm:flex-row sm:items-center sm:justify-between dark:border-slate-800 dark:bg-slate-900" style={{ marginLeft: `${depth * 1.25}rem` }}>
        <div>
          <p className="font-medium text-slate-950 dark:text-white">{category.name}</p>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            {category.code}{category.description ? ` · ${category.description}` : ""}
          </p>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => onEdit(category)} variant="outline">Edit</Button>
          <Button onClick={() => onDelete(category)} variant="ghost">Delete</Button>
        </div>
      </div>
      {category.children && category.children.length > 0 && (
        <ul className="space-y-2" role="group">
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
  const [values, setValues] = useState<CategoryFormState>(emptyForm);
  const categories = useQuery({ queryKey: ["categories"], queryFn: categoriesApi.list });
  const allCategories = useMemo(() => flattenCategories(categories.data ?? []), [categories.data]);

  useEffect(() => {
    if (!dialogOpen) return;
    setValues(editingCategory ? {
      code: editingCategory.code,
      name: editingCategory.name,
      parent_id: editingCategory.parent_id ?? "",
      description: editingCategory.description ?? "",
    } : emptyForm);
  }, [dialogOpen, editingCategory]);

  const saveCategory = useMutation({
    mutationFn: () => {
      const input: CategoryInput = {
        code: values.code,
        name: values.name,
        parent_id: values.parent_id || null,
        description: values.description || null,
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
          <p className="text-sm font-medium text-indigo-600 dark:text-indigo-400">Policy management</p>
          <h1 className="mt-1 text-2xl font-semibold text-slate-950 dark:text-white">Expense categories</h1>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Organize categories into a hierarchy for policy rules and report line items.</p>
        </div>
        <Button onClick={openCreate}>New category</Button>
      </header>

      {categories.isLoading && <p className="text-sm text-slate-600 dark:text-slate-300">Loading categories…</p>}
      {categories.isError && <p className="rounded-md bg-rose-50 p-3 text-sm text-rose-700 dark:bg-rose-950/40 dark:text-rose-200">Unable to load categories.</p>}
      {categories.data?.length === 0 && <p className="rounded-lg border border-dashed border-slate-300 p-8 text-center text-sm text-slate-600 dark:border-slate-700 dark:text-slate-300">No categories have been created.</p>}
      <ul className="space-y-2" role="tree">
        {categoryTree(categories.data ?? []).map((category) => (
          <CategoryBranch
            category={category}
            depth={0}
            key={category.id}
            onDelete={(selected) => {
              if (window.confirm(`Delete ${selected.name}?`)) deleteCategory.mutate(selected.id);
            }}
            onEdit={openEdit}
          />
        ))}
      </ul>

      <Dialog onOpenChange={setDialogOpen} open={dialogOpen}>
        <DialogContent>
          <DialogTitle>{editingCategory ? "Edit category" : "New category"}</DialogTitle>
          <DialogDescription>Use a parent category to create a nested hierarchy.</DialogDescription>
          <Form
            className="mt-5"
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
            {saveCategory.isError && <p className="text-sm text-rose-600">Unable to save this category.</p>}
            <div className="flex flex-col-reverse justify-end gap-2 pt-2 sm:flex-row">
              <Button onClick={() => setDialogOpen(false)} variant="outline">Cancel</Button>
              <Button disabled={saveCategory.isPending} type="submit">{saveCategory.isPending ? "Saving…" : "Save category"}</Button>
            </div>
          </Form>
        </DialogContent>
      </Dialog>
    </main>
  );
}
