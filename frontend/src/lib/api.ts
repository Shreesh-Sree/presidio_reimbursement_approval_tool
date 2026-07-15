import axios from "axios";

export type PolicyRule = {
  id?: string;
  category_id?: string;
  category_name?: string;
  vendor_id?: string;
  vendor_name?: string;
  max_per_day?: number | null;
  max_per_trip?: number | null;
  per_category_cap?: number | null;
  receipt_required_above?: number | null;
};

export type Policy = {
  id: string;
  name: string;
  version_label: string;
  effective_from: string;
  effective_to?: string | null;
  status: "draft" | "active" | "archived" | string;
  rules: PolicyRule[];
  document_url?: string | null;
  updated_at?: string;
};

export type PolicyInput = Pick<Policy, "name" | "version_label" | "effective_from"> & {
  effective_to?: string | null;
  rules: PolicyRule[];
};

export type Category = {
  id: string;
  code: string;
  name: string;
  parent_id?: string | null;
  description?: string | null;
  children?: Category[];
};

export type CategoryInput = Omit<Category, "id" | "children">;

export type Receipt = {
  id: string;
  url: string;
  file_name?: string;
  uploaded_at?: string;
};

export type ReportLineItem = {
  id: string;
  line_number?: number;
  category_id?: string;
  category_name?: string;
  vendor_id?: string;
  vendor_name?: string;
  amount: number;
  currency?: string;
  description: string;
  expense_date?: string;
  receipt?: Receipt | null;
  receipt_url?: string | null;
  is_policy_violated?: boolean;
  violation_reason?: string | null;
  policy_violation_reason?: string | null;
};

export type ApprovalHistoryEntry = {
  id: string;
  action: string;
  actor_name?: string;
  actor_id?: string;
  remarks?: string | null;
  created_at: string;
};

export type Report = {
  id: string;
  title: string;
  status: "draft" | "submitted" | "approved" | "rejected" | "sent_back" | string;
  total: number;
  currency?: string;
  created_at?: string;
  updated_at?: string;
  submitter_name?: string;
  submitter_email?: string;
  line_items?: ReportLineItem[];
  items?: ReportLineItem[];
  approval_history?: ApprovalHistoryEntry[];
  ai_audit?: Record<string, unknown> | null;
  violations?: string[];
};

export type ReportInput = {
  title: string;
  description?: string;
};

export type ReportLineItemInput = Omit<ReportLineItem, "id" | "receipt" | "receipt_url">;

export type ApprovalQueueItem = Pick<Report, "id" | "title" | "status" | "total" | "currency" | "created_at" | "submitter_name"> & {
  pending_with?: string;
};

export type Notification = {
  id: string;
  title: string;
  body?: string;
  created_at: string;
  read_at?: string | null;
  report_id?: string;
  type?: string;
};

export type ReportComment = {
  id: string;
  body: string;
  visibility: "internal" | "employee" | "all" | string;
  author_name?: string;
  author_id?: string;
  created_at: string;
};

export type SessionUser = {
  user_id: string;
  email: string;
  roles: string[];
  permissions?: string[];
};

export type LoginResponse = {
  access_token: string;
  token_type?: string;
  user?: SessionUser;
};

export type ManagedUser = {
  id: string;
  email: string;
  full_name?: string;
  status: string;
};

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "/api",
  headers: { "Content-Type": "application/json" },
});

let accessToken = typeof window === "undefined" ? null : window.localStorage.getItem("access_token");

export function setApiToken(token: string | null) {
  accessToken = token;

  if (typeof window !== "undefined") {
    if (token) window.localStorage.setItem("access_token", token);
    else window.localStorage.removeItem("access_token");
  }
}

apiClient.interceptors.request.use((config) => {
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`;
  return config;
});

const unwrap = <T>(request: Promise<{ data: T }>) => request.then((response) => response.data);

export const policiesApi = {
  list: () => unwrap(apiClient.get<Policy[]>("/policies")),
  create: (input: PolicyInput) => unwrap(apiClient.post<Policy>("/policies", input)),
  update: (policyId: string, input: PolicyInput) => unwrap(apiClient.patch<Policy>(`/policies/${policyId}`, input)),
  activate: (policyId: string) => unwrap(apiClient.post<Policy>(`/policies/${policyId}/activate`)),
  uploadDocument: (policyId: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return unwrap(
      apiClient.post<Policy>(`/policies/${policyId}/upload-doc`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      }),
    );
  },
};

export const authApi = {
  login: (email: string, password: string) => unwrap(apiClient.post<LoginResponse>("/auth/login", { email, password })),
  me: () => unwrap(apiClient.get<SessionUser>("/auth/me")),
  logout: () => unwrap(apiClient.post<void>("/auth/logout")),
};

export const usersApi = {
  list: () => unwrap(apiClient.get<ManagedUser[]>("/users")),
};

export const categoriesApi = {
  list: () => unwrap(apiClient.get<Category[]>("/categories")),
  create: (input: CategoryInput) => unwrap(apiClient.post<Category>("/categories", input)),
  update: (categoryId: string, input: Partial<CategoryInput>) =>
    unwrap(apiClient.patch<Category>(`/categories/${categoryId}`, input)),
  remove: (categoryId: string) => unwrap(apiClient.delete<void>(`/categories/${categoryId}`)),
};

export const reportsApi = {
  list: (status?: string) =>
    unwrap(apiClient.get<Report[]>("/reports", { params: status ? { status } : undefined })),
  create: (input: ReportInput) => unwrap(apiClient.post<Report>("/reports", input)),
  get: (reportId: string) => unwrap(apiClient.get<Report>(`/reports/${reportId}`)),
  update: (reportId: string, input: Partial<ReportInput>) =>
    unwrap(apiClient.patch<Report>(`/reports/${reportId}`, input)),
  submit: (reportId: string) => unwrap(apiClient.post<Report>(`/reports/${reportId}/submit`)),
  withdraw: (reportId: string) => unwrap(apiClient.post<Report>(`/reports/${reportId}/withdraw`)),
  listItems: (reportId: string) => unwrap(apiClient.get<ReportLineItem[]>(`/reports/${reportId}/items`)),
  addItem: (reportId: string, input: ReportLineItemInput) =>
    unwrap(apiClient.post<ReportLineItem>(`/reports/${reportId}/items`, input)),
  updateItem: (reportId: string, itemId: string, input: Partial<ReportLineItemInput>) =>
    unwrap(apiClient.patch<ReportLineItem>(`/reports/${reportId}/items/${itemId}`, input)),
  removeItem: (reportId: string, itemId: string) =>
    unwrap(apiClient.delete<void>(`/reports/${reportId}/items/${itemId}`)),
  uploadReceipt: (itemId: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return unwrap(
      apiClient.post<Receipt>(`/items/${itemId}/receipt`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      }),
    );
  },
};

export const approvalsApi = {
  queue: () => unwrap(apiClient.get<ApprovalQueueItem[]>("/approvals/queue")),
  approve: (reportId: string, remarks: string) =>
    unwrap(apiClient.post<Report>(`/approvals/${reportId}/approve`, { remarks })),
  reject: (reportId: string, remarks: string) =>
    unwrap(apiClient.post<Report>(`/approvals/${reportId}/reject`, { remarks })),
  sendBack: (reportId: string, remarks: string) =>
    unwrap(apiClient.post<Report>(`/approvals/${reportId}/send-back`, { remarks })),
};

export const notificationsApi = {
  list: () => unwrap(apiClient.get<Notification[]>("/notifications")),
  markRead: (notificationId: string) =>
    unwrap(apiClient.post<Notification>(`/notifications/${notificationId}/read`)),
};

export const commentsApi = {
  list: (reportId: string) => unwrap(apiClient.get<ReportComment[]>(`/reports/${reportId}/comments`)),
  create: (reportId: string, body: string, visibility: ReportComment["visibility"]) =>
    unwrap(apiClient.post<ReportComment>(`/reports/${reportId}/comments`, { body, visibility })),
};

export { apiClient };
