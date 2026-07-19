import { apiClient } from "../../lib/api";

export type Department = {
  id: string;
  code: string;
  name: string;
  status: "active" | "inactive" | string;
  department_head_user_id?: string | null;
};

export type DepartmentInput = {
  code: string;
  name: string;
};

export type DepartmentUpdateInput = Partial<DepartmentInput> & {
  status?: "active" | "inactive";
};

const unwrap = <T>(request: Promise<{ data: T }>) => request.then((response) => response.data);

export const departmentsApi = {
  list: (includeInactive = false) => unwrap(
    apiClient.get<Department[]>("/departments", { params: includeInactive ? { include_inactive: true } : undefined }),
  ),
  create: (input: DepartmentInput) => unwrap(apiClient.post<Department>("/departments", input)),
  update: (departmentId: string, input: DepartmentUpdateInput) =>
    unwrap(apiClient.patch<Department>(`/departments/${departmentId}`, input)),
};
