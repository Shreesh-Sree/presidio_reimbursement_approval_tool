import { useQuery } from "@tanstack/react-query";
import { usersApi } from "../../lib/api";

export function UsersPage() {
  const users = useQuery({ queryKey: ["users"], queryFn: usersApi.list });

  return (
    <main className="mx-auto w-full max-w-6xl space-y-6 p-4 sm:p-6">
      <header className="border-b border-slate-200 pb-5 dark:border-slate-800">
        <h1 className="text-2xl font-semibold text-slate-950 dark:text-white">Users</h1>
      </header>
      {users.isLoading && <p className="text-sm text-slate-600 dark:text-slate-300">Loading users…</p>}
      {users.isError && <p className="rounded-md bg-rose-50 p-3 text-sm text-rose-700 dark:bg-rose-950/40 dark:text-rose-200">Unable to load users.</p>}
      <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800">
      <table className="min-w-full divide-y divide-slate-200 text-left text-sm dark:divide-slate-800">
        <thead>
          <tr className="bg-slate-50 dark:bg-slate-900">
            <th className="px-4 py-3 font-medium">Email</th>
            <th className="px-4 py-3 font-medium">Name</th>
            <th className="px-4 py-3 font-medium">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
          {users.data?.map((user) => (
            <tr key={user.id}>
              <td className="px-4 py-3">{user.email}</td>
              <td className="px-4 py-3">{user.full_name || "N/A"}</td>
              <td className="px-4 py-3">{user.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>
    </main>
  );
}
