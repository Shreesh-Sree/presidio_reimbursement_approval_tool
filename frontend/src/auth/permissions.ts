export type PermissionUser = {
  roles: string[];
  permissions?: string[];
} | null;

export function isAdministrator(user: PermissionUser): boolean {
  if (!user) return false;
  return user.roles.some((role) => ["admin", "administrator"].includes(role.toLowerCase()));
}

const permissionsByRole: Record<string, string[]> = {
  admin: [
    "report:approve",
    "report:read",
    "policy:manage",
    "category:manage",
    "workflow:manage",
    "vendor:manage",
    "user:read",
    "user:update",
    "payment:manage",
    "access_request:manage",
  ],
  administrator: [
    "report:approve",
    "report:read",
    "policy:manage",
    "category:manage",
    "workflow:manage",
    "vendor:manage",
    "user:read",
    "user:update",
    "payment:manage",
    "access_request:manage",
  ],
  manager: [
    "report:approve",
    "report:read",
    "policy:manage",
    "category:manage",
    "workflow:manage",
    "vendor:manage",
    "user:read",
    "payment:manage",
  ],
  approver: ["report:approve", "report:read"],
  employee: ["report:create", "report:read", "employee:access"],
};

export function isManager(user: PermissionUser): boolean {
  if (!user) return false;
  return user.roles.some((role) => ["manager", "department_head", "approver"].includes(role.toLowerCase()));
}

export function isFinance(user: PermissionUser): boolean {
  if (!user) return false;
  return user.roles.some((role) => ["finance", "finance_auditor"].includes(role.toLowerCase()));
}

export function getDefaultHomeRoute(user: PermissionUser): string {
  if (!user) return "/sign-in";
  if (isAdministrator(user)) return "/approvals";
  if (isFinance(user)) return "/payments";
  if (isManager(user)) return "/approvals";
  return "/reports";
}

export function hasPermission(user: PermissionUser, permission: string) {
  if (!user) return false;
  
  // Administrator only has Manager & Finance features; strictly exclude employee pages & report creation
  if (
    (permission === "report:create" || permission === "employee:access") &&
    isAdministrator(user) &&
    !user.roles.some((r) => r.toLowerCase() === "employee")
  ) {
    return false;
  }

  if (user.permissions?.includes("*") || user.permissions?.includes(permission)) return true;
  return user.roles.some((role) => permissionsByRole[role.toLowerCase()]?.includes("*") || permissionsByRole[role.toLowerCase()]?.includes(permission));
}

