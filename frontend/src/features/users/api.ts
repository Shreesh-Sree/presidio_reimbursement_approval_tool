import { apiClient } from "../../lib/api";

export type RoleOption = {
  code: string;
  name: string;
};

export type ManagedUser = {
  id: string;
  email: string;
  full_name: string;
  status: string;
  roles: string[];
  oauth_status?: "invited" | "linked";
  organization_id?: string;
  organization_name?: string | null;
  organization_code?: string | null;
  department_id?: string;
  department_name?: string | null;
  manager_id?: string | null;
  manager_name?: string | null;
};

export type UserInput = {
  email: string;
  full_name: string;
  roles: string[];
  manager_id?: string | null;
  department_id?: string | null;
};

export type OrgChartNode = {
  id: string;
  name: string;
  email?: string | null;
  roles: string[];
  reports: OrgChartNode[];
};

type ApiRole = string | RoleOption;
type ApiManagedUser = Omit<ManagedUser, "roles"> & { roles?: ApiRole[] };
type UserListResponse = ApiManagedUser[] | { users?: ApiManagedUser[]; data?: ApiManagedUser[] };
type OrgChartResponse = OrgChartNodeInput[] | { roots?: OrgChartNodeInput[]; nodes?: OrgChartNodeInput[]; data?: OrgChartNodeInput[] };
type OrgChartNodeInput = Omit<Partial<OrgChartNode>, "roles" | "reports"> & {
  id: string;
  name?: string;
  full_name?: string;
  roles?: ApiRole[];
  reports?: OrgChartNodeInput[];
  direct_reports?: OrgChartNodeInput[];
  children?: OrgChartNodeInput[];
};

const unwrap = <T>(request: Promise<{ data: T }>) => request.then((response) => response.data);

function roleCode(role: ApiRole) {
  return typeof role === "string" ? role : role.code;
}

function normalizeUser(user: ApiManagedUser): ManagedUser {
  return {
    ...user,
    full_name: user.full_name || user.email,
    roles: (user.roles ?? []).map(roleCode),
  };
}

function normalizeUsers(response: UserListResponse) {
  const users = Array.isArray(response) ? response : response.users ?? response.data ?? [];
  return users.map(normalizeUser);
}

function normalizeNode(node: OrgChartNodeInput): OrgChartNode {
  return {
    id: node.id,
    name: node.name ?? node.full_name ?? "Unnamed user",
    email: node.email,
    roles: (node.roles ?? []).map(roleCode),
    reports: (node.reports ?? node.direct_reports ?? node.children ?? []).map(normalizeNode),
  };
}

function normalizeOrgChart(response: OrgChartResponse) {
  const roots = Array.isArray(response) ? response : response.roots ?? response.nodes ?? response.data ?? [];
  return roots.map(normalizeNode);
}

/**
 * User administration is intentionally feature-local while the backend's user
 * contract is being stabilized. Pages only depend on this adapter, rather than
 * on URLs or axios directly.
 */
export const userAdminApi = {
  list: () => unwrap(apiClient.get<UserListResponse>("/users")).then(normalizeUsers),
  get: (userId: string) => unwrap(apiClient.get<ApiManagedUser>(`/users/${userId}`)).then(normalizeUser),
  create: (input: UserInput) => unwrap(apiClient.post<ApiManagedUser>("/users", input)).then(normalizeUser),
  // Supabase owns verified email addresses.  Do not send the form's display
  // value on an edit, otherwise the API correctly rejects every update.
  update: (userId: string, input: UserInput) =>
    unwrap(apiClient.patch<ApiManagedUser>(`/users/${userId}`, {
      full_name: input.full_name,
      roles: input.roles,
      manager_id: input.manager_id,
      department_id: input.department_id,
    })).then(normalizeUser),
  deactivate: (userId: string) =>
    unwrap(apiClient.post<ApiManagedUser>(`/users/${userId}/deactivate`)).then(normalizeUser),
  bulkCreate: (file: File) => {
    const form = new FormData(); form.append("file", file);
    return unwrap(apiClient.post<{ created_count: number; error_count: number; errors: Array<{ row: number; email: string; message: string }> }>("/users/bulk", form));
  },
  listRoles: () => unwrap(apiClient.get<RoleOption[]>("/roles")),
  orgChart: () => unwrap(apiClient.get<OrgChartResponse>("/org-chart")).then(normalizeOrgChart),
};
