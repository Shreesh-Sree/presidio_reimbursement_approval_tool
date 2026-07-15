export type PermissionUser = {
  roles: string[];
  permissions?: string[];
} | null;

const permissionsByRole: Record<string, string[]> = {
  admin: ["*"],
  administrator: ["*"],
  manager: ["report:approve", "report:read"],
  approver: ["report:approve", "report:read"],
  employee: ["report:create", "report:read"],
};

export function hasPermission(user: PermissionUser, permission: string) {
  if (!user) return false;
  if (user.permissions?.includes("*") || user.permissions?.includes(permission)) return true;
  return user.roles.some((role) => permissionsByRole[role.toLowerCase()]?.includes("*") || permissionsByRole[role.toLowerCase()]?.includes(permission));
}
