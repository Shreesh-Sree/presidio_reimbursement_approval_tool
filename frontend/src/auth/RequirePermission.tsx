import type { ReactNode } from "react";
import { useAuth } from "./AuthContext";

type RequirePermissionProps = {
  permission: string;
  children: ReactNode;
};

const permissionsByRole: Record<string, string[]> = {
  admin: ["*"],
  administrator: ["*"],
  manager: ["report:approve", "report:read"],
  approver: ["report:approve", "report:read"],
  employee: ["report:create", "report:read"],
};

function hasPermission(user: { roles: string[]; permissions?: string[] } | null, permission: string) {
  if (!user) return false;
  if (user.permissions?.includes("*") || user.permissions?.includes(permission)) return true;
  return user.roles.some((role) => permissionsByRole[role.toLowerCase()]?.includes("*") || permissionsByRole[role.toLowerCase()]?.includes(permission));
}

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
