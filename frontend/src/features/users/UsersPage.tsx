import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "../../components/ui/button";
import { LoadingState } from "../../components/ui/loading-state";
import { getApiErrorMessage } from "../../lib/api";
import { departmentsApi } from "../departments/api";
import { type ManagedUser, type UserInput, userAdminApi } from "./api";
import { UserForm } from "./UserForm";

function labelForStatus(status: string) {
  return status.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function labelForRole(role: string) {
  if (role === "approver") return "Manager / Approver";
  return role.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function UsersPage() {
  const queryClient = useQueryClient();
  const [formOpen, setFormOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<ManagedUser | null>(null);
  const [bulkFile, setBulkFile] = useState<File | null>(null);
  const users = useQuery({ queryKey: ["users"], queryFn: userAdminApi.list });
  const roles = useQuery({ queryKey: ["roles"], queryFn: userAdminApi.listRoles });
  const departments = useQuery({ queryKey: ["departments", "active"], queryFn: () => departmentsApi.list() });

  const refreshUserData = () => {
    queryClient.invalidateQueries({ queryKey: ["users"] });
    queryClient.invalidateQueries({ queryKey: ["org-chart"] });
  };

  const saveUser = useMutation({
    mutationFn: (input: UserInput) => editingUser
      ? userAdminApi.update(editingUser.id, input)
      : userAdminApi.create(input),
    onSuccess: () => {
      refreshUserData();
      setFormOpen(false);
    },
  });

  const deactivateUser = useMutation({
    mutationFn: (userId: string) => userAdminApi.deactivate(userId),
    onSuccess: refreshUserData,
  });
  const bulkCreate = useMutation({
    mutationFn: userAdminApi.bulkCreate,
    onSuccess: () => { refreshUserData(); setBulkFile(null); },
  });

  const openCreate = () => {
    saveUser.reset();
    setEditingUser(null);
    setFormOpen(true);
  };

  const openEdit = (user: ManagedUser) => {
    saveUser.reset();
    setEditingUser(user);
    setFormOpen(true);
  };

  return (
    <main className="mx-auto w-full max-w-6xl space-y-6 p-4 sm:p-6">
      <header className="flex flex-col gap-4 border-b border-slate-200 pb-5 sm:flex-row sm:items-center sm:justify-between dark:border-slate-800">
        <div>
          <p className="text-sm font-medium text-orange-600 dark:text-orange-400">Administration</p>
          <h1 className="mt-1 text-2xl font-semibold text-slate-950 dark:text-white">Users and reporting lines</h1>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Invite work emails, manage the four platform roles, and maintain the reporting structure.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <label className="inline-flex min-h-11 cursor-pointer items-center rounded-full border border-[#202020] bg-white px-5 py-2.5 text-sm font-bold text-[#202020] dark:border-white dark:bg-[#202020] dark:text-white">
            <input accept=".csv,text/csv" className="sr-only" onChange={(event) => setBulkFile(event.target.files?.[0] ?? null)} type="file" />
            {bulkFile ? bulkFile.name : "Choose CSV"}
          </label>
          <Button disabled={!bulkFile || bulkCreate.isPending} onClick={() => bulkFile && bulkCreate.mutate(bulkFile)} variant="outline">{bulkCreate.isPending ? "Inviting…" : "Bulk invite"}</Button>
          <Button disabled={roles.isLoading || roles.isError || departments.isLoading || departments.isError || !(departments.data?.length)} onClick={openCreate}>Invite user</Button>
        </div>
      </header>

      {users.isLoading && <LoadingState label="Loading users" />}
      {users.isError && <p className="rounded-md bg-orange-50 p-3 text-sm text-orange-700 dark:bg-orange-950/40 dark:text-orange-200">Unable to load users.</p>}
      {roles.isError && <p className="rounded-md bg-orange-50 p-3 text-sm text-orange-700 dark:bg-orange-950/40 dark:text-orange-200">Unable to load available roles.</p>}
      {departments.isError && <p className="rounded-md bg-orange-50 p-3 text-sm text-orange-700 dark:bg-orange-950/40 dark:text-orange-200">{getApiErrorMessage(departments.error, "Unable to load departments. Create or restore a department before inviting users.")}</p>}
      {bulkCreate.isError && <p className="rounded-md bg-orange-50 p-3 text-sm text-orange-700" role="alert">{getApiErrorMessage(bulkCreate.error, "Bulk invite failed. Use a CSV with email, full_name, and semicolon-separated roles columns.")}</p>}
      {bulkCreate.data && <p className="rounded-md bg-orange-50 p-3 text-sm text-orange-800">Invited {bulkCreate.data.created_count} user(s); {bulkCreate.data.error_count} row(s) need review.</p>}

      {users.data?.length === 0 && (
        <div className="rounded-lg border border-dashed border-slate-300 p-8 text-center text-sm text-slate-600 dark:border-slate-700 dark:text-slate-300">
          No users have been invited yet.
        </div>
      )}

      <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800">
        <table className="min-w-full divide-y divide-slate-200 text-left text-sm dark:divide-slate-800">
          <thead>
            <tr className="bg-slate-50 dark:bg-slate-900">
              <th className="px-4 py-3 font-medium">User</th>
              <th className="px-4 py-3 font-medium">Organisation</th>
              <th className="px-4 py-3 font-medium">Department</th>
              <th className="px-4 py-3 font-medium">Roles</th>
              <th className="px-4 py-3 font-medium">Reporting manager</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium"><span className="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
            {users.data?.map((user) => {
              const isActive = user.status.toLowerCase() === "active";
              return (
                <tr key={user.id}>
                  <td className="px-4 py-3">
                    <p className="font-medium text-slate-950 dark:text-white">{user.full_name}</p>
                    <p className="text-slate-600 dark:text-slate-300">{user.email}</p>
                  </td>
                  <td className="px-4 py-3 text-slate-700 dark:text-slate-200">
                    <p className="font-medium">{user.organization_name ?? "Organisation unavailable"}</p>
                    {user.organization_code && <p className="text-xs text-slate-500 dark:text-slate-400">{user.organization_code}</p>}
                  </td>
                  <td className="px-4 py-3 text-slate-700 dark:text-slate-200">{user.department_name ?? "General"}</td>
                  <td className="px-4 py-3">
                    <div className="flex min-w-40 flex-wrap gap-1">
                      {user.roles.length > 0 ? user.roles.map((role) => (
                        <span className="rounded-full bg-orange-50 px-2 py-0.5 text-xs font-medium text-orange-700 dark:bg-orange-950/50 dark:text-orange-200" key={role}>
                          {labelForRole(role)}
                        </span>
                      )) : <span className="text-slate-500 dark:text-slate-400">No roles</span>}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-slate-700 dark:text-slate-200">{user.manager_name ?? "No reporting manager"}</td>
                  <td className="px-4 py-3">
                    <span className={isActive ? "rounded-full bg-orange-100 px-2.5 py-1 text-xs font-semibold text-orange-700 dark:bg-orange-950 dark:text-orange-300" : "rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700 dark:bg-slate-800 dark:text-slate-200"}>
                      {labelForStatus(user.status)}
                    </span>
                    {user.oauth_status === "invited" && <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Invitation pending</p>}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap justify-end gap-2">
                      <Button aria-label={`Edit ${user.full_name}`} onClick={() => openEdit(user)} variant="outline">Edit</Button>
                      <Button
                        aria-label={`Deactivate ${user.full_name}`}
                        disabled={!isActive || deactivateUser.isPending}
                        onClick={() => deactivateUser.mutate(user.id)}
                        variant="destructive"
                      >
                        Deactivate
                      </Button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {deactivateUser.isError && <p className="text-sm text-orange-600 dark:text-orange-300" role="alert">{getApiErrorMessage(deactivateUser.error, "Unable to deactivate this user.")}</p>}

      <UserForm
        isError={saveUser.isError}
        isPending={saveUser.isPending}
        errorMessage={saveUser.isError ? getApiErrorMessage(saveUser.error, "Unable to save this user. Review the details and try again.") : undefined}
        onOpenChange={setFormOpen}
        onSubmit={(input) => saveUser.mutate(input)}
        open={formOpen}
        departments={departments.data ?? []}
        roles={roles.data ?? []}
        user={editingUser}
        users={users.data ?? []}
      />
    </main>
  );
}
