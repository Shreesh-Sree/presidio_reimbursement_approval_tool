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
  manager_id?: string | null;
  manager_name?: string | null;
};

export type UserInput = {
  email: string;
  full_name: string;
  roles: string[];
  manager_id?: string | null;
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
  update: (userId: string, input: UserInput) =>
    unwrap(apiClient.patch<ApiManagedUser>(`/users/${userId}`, input)).then(normalizeUser),
  deactivate: (userId: string) =>
    unwrap(apiClient.post<ApiManagedUser>(`/users/${userId}/deactivate`)).then(normalizeUser),
  listRoles: () => unwrap(apiClient.get<RoleOption[]>("/roles")),
  orgChart: () => unwrap(apiClient.get<OrgChartResponse>("/org-chart")).then(normalizeOrgChart),
};
