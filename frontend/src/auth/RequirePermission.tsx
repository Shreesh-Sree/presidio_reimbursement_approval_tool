import type { ReactNode } from "react";
import { useAuth } from "./AuthContext";
import { hasPermission } from "./permissions";

type RequirePermissionProps = {
  permission: string;
  children: ReactNode;
};

export function RequirePermission({ permission, children }: RequirePermissionProps) {
  const { user } = useAuth();

  if (hasPermission(user, permission)) return <>{children}</>;

  return (
    <main className="mx-auto flex min-h-[60vh] w-full max-w-xl items-center justify-center p-6">
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-6 text-center dark:border-amber-900 dark:bg-amber-950/40">
        <h1 className="text-lg font-semibold text-amber-950 dark:text-amber-100">Permission required</h1>
        <p className="mt-2 text-sm text-amber-800 dark:text-amber-200">You do not have access to this page.</p>
      </div>
    </main>
  );
}
