import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "../../components/ui/button";
import { type ManagedUser, type UserInput, userAdminApi } from "./api";
import { UserForm } from "./UserForm";

function labelForStatus(status: string) {
  return status.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function labelForRole(role: string) {
  return role.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function UsersPage() {
  const queryClient = useQueryClient();
  const [formOpen, setFormOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<ManagedUser | null>(null);
  const users = useQuery({ queryKey: ["users"], queryFn: userAdminApi.list });
  const roles = useQuery({ queryKey: ["roles"], queryFn: userAdminApi.listRoles });

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
          <p className="text-sm font-medium text-indigo-600 dark:text-indigo-400">Administration</p>
          <h1 className="mt-1 text-2xl font-semibold text-slate-950 dark:text-white">Users and reporting lines</h1>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Manage access roles and assign each employee to their reporting manager.</p>
        </div>
        <Button disabled={roles.isLoading || roles.isError} onClick={openCreate}>New user</Button>
      </header>

      {users.isLoading && <p className="text-sm text-slate-600 dark:text-slate-300">Loading users…</p>}
      {users.isError && <p className="rounded-md bg-rose-50 p-3 text-sm text-rose-700 dark:bg-rose-950/40 dark:text-rose-200">Unable to load users.</p>}
      {roles.isError && <p className="rounded-md bg-rose-50 p-3 text-sm text-rose-700 dark:bg-rose-950/40 dark:text-rose-200">Unable to load available roles.</p>}

      {users.data?.length === 0 && (
        <div className="rounded-lg border border-dashed border-slate-300 p-8 text-center text-sm text-slate-600 dark:border-slate-700 dark:text-slate-300">
          No users have been created yet.
        </div>
      )}

      <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800">
        <table className="min-w-full divide-y divide-slate-200 text-left text-sm dark:divide-slate-800">
          <thead>
            <tr className="bg-slate-50 dark:bg-slate-900">
              <th className="px-4 py-3 font-medium">User</th>
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
                  <td className="px-4 py-3">
                    <div className="flex min-w-40 flex-wrap gap-1">
                      {user.roles.length > 0 ? user.roles.map((role) => (
                        <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700 dark:bg-indigo-950/50 dark:text-indigo-200" key={role}>
                          {labelForRole(role)}
                        </span>
                      )) : <span className="text-slate-500 dark:text-slate-400">No roles</span>}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-slate-700 dark:text-slate-200">{user.manager_name ?? "No reporting manager"}</td>
                  <td className="px-4 py-3">
                    <span className={isActive ? "rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-semibold text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300" : "rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700 dark:bg-slate-800 dark:text-slate-200"}>
                      {labelForStatus(user.status)}
                    </span>
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

      {deactivateUser.isError && <p className="text-sm text-rose-600 dark:text-rose-300" role="alert">Unable to deactivate this user.</p>}

      <UserForm
        isError={saveUser.isError}
        isPending={saveUser.isPending}
        onOpenChange={setFormOpen}
        onSubmit={(input) => saveUser.mutate(input)}
        open={formOpen}
        roles={roles.data ?? []}
        user={editingUser}
        users={users.data ?? []}
      />
    </main>
  );
}
