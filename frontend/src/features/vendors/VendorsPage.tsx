import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "../../components/ui/button";
import { LoadingState } from "../../components/ui/loading-state";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "../../components/ui/dialog";
import { ConfirmDialog } from "../../components/ui/confirm-dialog";
import { Form, FormField } from "../../components/ui/form";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { vendorsApi, type Vendor } from "../../lib/api";

type VendorFormState = {
  name: string;
  normalized_name: string;
  description: string;
};

const emptyForm: VendorFormState = { name: "", normalized_name: "", description: "" };

export function VendorsPage() {
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingVendor, setEditingVendor] = useState<Vendor | null>(null);
  const [deletingVendor, setDeletingVendor] = useState<Vendor | null>(null);
  const [values, setValues] = useState<VendorFormState>(emptyForm);
  const vendors = useQuery({ queryKey: ["vendors"], queryFn: vendorsApi.list });

  useEffect(() => {
    if (!dialogOpen) return;
    setValues(editingVendor ? {
      name: editingVendor.name,
      normalized_name: editingVendor.normalized_name ?? "",
      description: (editingVendor as Record<string, unknown>).description as string ?? "",
    } : emptyForm);
  }, [dialogOpen, editingVendor]);

  const saveVendor = useMutation({
    mutationFn: () => {
      const input = {
        name: values.name.trim(),
        normalized_name: values.normalized_name.trim() || null,
        description: values.description.trim() || null,
      };
      return editingVendor ? vendorsApi.update(editingVendor.id, input) : vendorsApi.create(input);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["vendors"] });
      setDialogOpen(false);
    },
  });

  const deleteVendor = useMutation({
    mutationFn: vendorsApi.remove,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["vendors"] }),
  });

  const openCreate = () => {
    setEditingVendor(null);
    setDialogOpen(true);
  };

  const openEdit = (vendor: Vendor) => {
    setEditingVendor(vendor);
    setDialogOpen(true);
  };

  return (
    <main className="mx-auto w-full max-w-5xl space-y-6 p-4 sm:p-6">
      <header className="flex flex-col gap-4 border-b border-slate-200 pb-5 sm:flex-row sm:items-center sm:justify-between dark:border-slate-800">
        <div>
          <p className="text-sm font-medium text-orange-600 dark:text-orange-400">Policy management</p>
          <h1 className="mt-1 text-2xl font-semibold text-slate-950 dark:text-white">Vendors</h1>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Manage approved vendors for expense line items and policy rules.</p>
        </div>
        <Button onClick={openCreate}>New vendor</Button>
      </header>

      {vendors.isLoading && <LoadingState label="Loading vendors" />}
      {vendors.isError && <p className="rounded-md bg-orange-50 p-3 text-sm text-orange-700 dark:bg-orange-950/40 dark:text-orange-200">Unable to load vendors.</p>}
      {vendors.data?.length === 0 && <p className="rounded-lg border border-dashed border-slate-300 p-8 text-center text-sm text-slate-600 dark:border-slate-700 dark:text-slate-300">No vendors have been created.</p>}

      <div className="space-y-2">
        {vendors.data?.map((vendor) => (
          <div
            key={vendor.id}
            className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:flex-row sm:items-center sm:justify-between dark:border-slate-800 dark:bg-slate-900"
          >
            <div>
              <p className="font-semibold text-slate-950 dark:text-white">{vendor.name}</p>
              {vendor.normalized_name && (
                <p className="text-sm text-slate-600 dark:text-slate-300">Normalized: {vendor.normalized_name}</p>
              )}
            </div>
            <div className="flex gap-2">
              <Button onClick={() => openEdit(vendor)} variant="outline">Edit</Button>
              <Button onClick={() => setDeletingVendor(vendor)} variant="ghost">Delete</Button>
            </div>
          </div>
        ))}
      </div>

      <Dialog onOpenChange={setDialogOpen} open={dialogOpen}>
        <DialogContent>
          <DialogTitle>{editingVendor ? "Edit vendor" : "New vendor"}</DialogTitle>
          <DialogDescription>Vendors are available in expense line items and policy rules.</DialogDescription>
          <Form
            className="mt-5"
            onSubmit={(event) => {
              event.preventDefault();
              saveVendor.mutate();
            }}
          >
            <FormField>
              <Label htmlFor="vendor-name">Name</Label>
              <Input id="vendor-name" onChange={(event) => setValues((current) => ({ ...current, name: event.target.value }))} required value={values.name} />
            </FormField>
            <FormField>
              <Label htmlFor="vendor-normalized">Normalized name (optional)</Label>
              <Input id="vendor-normalized" onChange={(event) => setValues((current) => ({ ...current, normalized_name: event.target.value }))} value={values.normalized_name} placeholder="Used for duplicate detection" />
            </FormField>
            <FormField>
              <Label htmlFor="vendor-description">Description (optional)</Label>
              <Input id="vendor-description" onChange={(event) => setValues((current) => ({ ...current, description: event.target.value }))} value={values.description} />
            </FormField>
            {saveVendor.isError && <p className="text-sm text-orange-600">Unable to save this vendor.</p>}
            <div className="flex flex-col-reverse justify-end gap-2 pt-2 sm:flex-row">
              <Button onClick={() => setDialogOpen(false)} variant="outline">Cancel</Button>
              <Button disabled={saveVendor.isPending} type="submit">{saveVendor.isPending ? "Saving…" : "Save vendor"}</Button>
            </div>
          </Form>
        </DialogContent>
      </Dialog>
      <ConfirmDialog
        description={`Delete ${deletingVendor?.name ?? "this vendor"}? This cannot be undone.`}
        onConfirm={() => deletingVendor && deleteVendor.mutate(deletingVendor.id, { onSuccess: () => setDeletingVendor(null) })}
        onOpenChange={(open) => !open && setDeletingVendor(null)}
        open={Boolean(deletingVendor)}
        title="Delete vendor"
      />
    </main>
  );
}
