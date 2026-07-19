import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "../../components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "../../components/ui/dialog";
import { Form, FormField } from "../../components/ui/form";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { LoadingState } from "../../components/ui/loading-state";
import { Select } from "../../components/ui/select";
import { getApiErrorMessage } from "../../lib/api";
import { departmentsApi, type Department } from "./api";

type DepartmentFormValues = {
  code: string;
  name: string;
  status: "active" | "inactive";
};

const emptyValues: DepartmentFormValues = { code: "", name: "", status: "active" };

function valuesFor(department: Department | null): DepartmentFormValues {
  return department
    ? { code: department.code, name: department.name, status: department.status === "inactive" ? "inactive" : "active" }
    : emptyValues;
}

export function DepartmentsPage() {
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingDepartment, setEditingDepartment] = useState<Department | null>(null);
  const [values, setValues] = useState<DepartmentFormValues>(emptyValues);
  const departments = useQuery({ queryKey: ["departments", "all"], queryFn: () => departmentsApi.list(true) });

  useEffect(() => {
    if (dialogOpen) setValues(valuesFor(editingDepartment));
  }, [dialogOpen, editingDepartment]);

  const saveDepartment = useMutation({
    mutationFn: () => {
      const input = { code: values.code.trim(), name: values.name.trim() };
      return editingDepartment
        ? departmentsApi.update(editingDepartment.id, { ...input, status: values.status })
        : departmentsApi.create(input);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["departments"] });
      setDialogOpen(false);
    },
  });

  const openCreate = () => {
    saveDepartment.reset();
    setEditingDepartment(null);
    setDialogOpen(true);
  };

  const openEdit = (department: Department) => {
    saveDepartment.reset();
    setEditingDepartment(department);
    setDialogOpen(true);
  };

  return (
    <main className="mx-auto w-full max-w-5xl space-y-6 p-4 sm:p-6">
      <header className="flex flex-col gap-4 border-b border-slate-200 pb-5 sm:flex-row sm:items-center sm:justify-between dark:border-slate-800">
        <div>
          <p className="text-sm font-medium text-orange-600 dark:text-orange-400">Organisation administration</p>
          <h1 className="mt-1 text-2xl font-semibold text-slate-950 dark:text-white">Departments</h1>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Create departments and keep employee assignments current.</p>
        </div>
        <Button onClick={openCreate}>New department</Button>
      </header>

      {departments.isLoading && <LoadingState label="Loading departments" />}
      {departments.isError && <p className="rounded-md bg-orange-50 p-3 text-sm text-orange-700 dark:bg-orange-950/40 dark:text-orange-200" role="alert">{getApiErrorMessage(departments.error, "Unable to load departments.")}</p>}
      {departments.data?.length === 0 && <p className="rounded-lg border border-dashed border-slate-300 p-8 text-center text-sm text-slate-600 dark:border-slate-700 dark:text-slate-300">No departments have been created.</p>}

      <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800">
        <table className="min-w-full divide-y divide-slate-200 text-left text-sm dark:divide-slate-800">
          <thead><tr className="bg-slate-50 dark:bg-slate-900"><th className="px-4 py-3 font-medium">Department</th><th className="px-4 py-3 font-medium">Code</th><th className="px-4 py-3 font-medium">Status</th><th className="px-4 py-3"><span className="sr-only">Actions</span></th></tr></thead>
          <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
            {departments.data?.map((department) => (
              <tr key={department.id}>
                <td className="px-4 py-3 font-medium text-slate-950 dark:text-white">{department.name}</td>
                <td className="px-4 py-3 text-slate-700 dark:text-slate-200">{department.code}</td>
                <td className="px-4 py-3"><span className={department.status === "active" ? "rounded-full bg-orange-100 px-2.5 py-1 text-xs font-semibold text-orange-700 dark:bg-orange-950 dark:text-orange-300" : "rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700 dark:bg-slate-800 dark:text-slate-200"}>{department.status === "active" ? "Active" : "Inactive"}</span></td>
                <td className="px-4 py-3 text-right"><Button aria-label={`Edit ${department.name}`} onClick={() => openEdit(department)} variant="outline">Edit</Button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Dialog onOpenChange={setDialogOpen} open={dialogOpen}>
        <DialogContent>
          <DialogTitle>{editingDepartment ? "Edit department" : "New department"}</DialogTitle>
          <DialogDescription>{editingDepartment ? "Move employees to another active department before deactivating this one." : "Employees can be assigned to this department when they are invited or edited."}</DialogDescription>
          <Form className="mt-5" onSubmit={(event) => { event.preventDefault(); saveDepartment.mutate(); }}>
            <FormField>
              <Label htmlFor="department-name">Name</Label>
              <Input id="department-name" onChange={(event) => setValues((current) => ({ ...current, name: event.target.value }))} required value={values.name} />
            </FormField>
            <FormField>
              <Label htmlFor="department-code">Code</Label>
              <Input id="department-code" maxLength={50} onChange={(event) => setValues((current) => ({ ...current, code: event.target.value }))} required value={values.code} />
            </FormField>
            {editingDepartment && (
              <FormField>
                <Label htmlFor="department-status">Status</Label>
                <Select id="department-status" onChange={(event) => setValues((current) => ({ ...current, status: event.target.value as DepartmentFormValues["status"] }))} value={values.status}>
                  <option value="active">Active</option>
                  <option value="inactive">Inactive</option>
                </Select>
              </FormField>
            )}
            {saveDepartment.isError && <p className="text-sm text-orange-600 dark:text-orange-300" role="alert">{getApiErrorMessage(saveDepartment.error, "Unable to save this department.")}</p>}
            <div className="flex flex-col-reverse justify-end gap-2 pt-2 sm:flex-row">
              <Button onClick={() => setDialogOpen(false)} variant="outline">Cancel</Button>
              <Button disabled={saveDepartment.isPending} type="submit">{saveDepartment.isPending ? "Saving…" : editingDepartment ? "Save changes" : "Create department"}</Button>
            </div>
          </Form>
        </DialogContent>
      </Dialog>
    </main>
  );
}
