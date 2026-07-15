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

/**
 * These contracts intentionally contain only policy-version evidence. The
 * assistant is advisory: it cannot make workflow or payment decisions.
 */
export type PolicyAssistantCitation = {
  document_ref: string;
  source_chunk_id: string;
  excerpt: string;
  similarity: number;
};

export type PolicyAssistantIndexing = {
  document_ref: string;
  document_digest: string;
  chunk_count: number;
  injection_flags: string[];
};

export type PolicyAssistantIndexResponse = {
  policy_id: string;
  indexing: PolicyAssistantIndexing;
};

export type PolicyAssistantQuestion = {
  question: string;
  top_k?: number;
};

export type PolicyAssistantAnswer = {
  answer: string;
  evidence_found: boolean;
  citations: PolicyAssistantCitation[];
};

export type PolicyAssistantAskResponse = {
  policy_id: string;
  answer: PolicyAssistantAnswer;
};

export type WorkflowConditions = {
  min_total?: number | null;
  max_total?: number | null;
  department_id?: string | null;
  currency_code?: string | null;
};

export type WorkflowApprovalStep = {
  manager_level?: number;
  user_id?: string;
  role_code?: string;
};

export type WorkflowRule = {
  id: string;
  name: string;
  conditions: WorkflowConditions;
  approval_chain: WorkflowApprovalStep[];
  priority: number;
  is_active: boolean;
  created_at?: string | null;
  updated_at?: string | null;
};

export type WorkflowRuleInput = Omit<WorkflowRule, "id" | "created_at" | "updated_at">;

export type WorkflowRoleOption = {
  code: string;
  name: string;
};

export type Category = {
  id: string;
  code: string;
  name: string;
  parent_id?: string | null;
  description?: string | null;
  receipt_required?: boolean;
  max_amount?: number | null;
  children?: Category[];
};

export type CategoryInput = Omit<Category, "id" | "children">;

export type Vendor = {
  id: string;
  name: string;
  normalized_name?: string | null;
};

export type Receipt = {
  id: string;
  url: string;
  file_name?: string;
  uploaded_at?: string;
};

/** Ephemeral, metadata-only advice from the isolated receipt service. */
export type ReceiptAnalysisFinding = {
  code: string;
  severity?: "info" | "warning" | "error" | string;
  message?: string;
};

export type ReceiptAnalysisResponse = {
  advisory: true;
  context: {
    organization_ref: string;
    report_ref: string;
    item_ref: string;
    attachment_ref?: string | null;
    event_id: string;
  };
  analysis: {
    findings?: ReceiptAnalysisFinding[];
    ocr?: { performed?: boolean };
  };
};

export type ReportLineItem = {
  id: string;
  line_number?: number;
  category_id?: string;
  category_name?: string;
  vendor_id?: string;
  vendor_name?: string;
  merchant_name?: string | null;
  amount: number;
  currency?: string;
  currency_code?: string;
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
  acting_for_name?: string | null;
  acting_for_user_id?: string | null;
  remarks?: string | null;
  created_at: string;
};

/** Employee-safe reimbursement tracking data returned with a report. */
export type ReportPayment = {
  id: string;
  payment_reference: string;
  status: "pending" | "batched" | "exported" | "paid" | "failed" | string;
  payment_date?: string | null;
  exported_at?: string | null;
  batch?: {
    id: string;
    batch_reference: string;
    status: string;
  } | null;
};

export type Report = {
  id: string;
  title: string;
  description?: string | null;
  start_date?: string | null;
  end_date?: string | null;
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
  payment?: ReportPayment | null;
  ai_audit?: Record<string, unknown> | null;
  violations?: string[];
};

export type ReportInput = {
  title: string;
  description?: string;
  start_date?: string;
  end_date?: string;
  currency?: string;
};

export type ReportLineItemInput = {
  category_id: string;
  vendor_id?: string | null;
  merchant_name?: string | null;
  amount: number;
  currency?: string;
  description: string;
  expense_date?: string;
};

export type ApprovalQueueItem = Pick<Report, "id" | "title" | "status" | "total" | "currency" | "created_at" | "submitter_name"> & {
  pending_with?: string;
  approval_status?: string;
  approval_decision_at?: string | null;
  acting_for_name?: string | null;
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

export type CurrencyAmount = {
  currency: string;
  amount: number;
};

export type AnalyticsCategorySpend = CurrencyAmount & {
  category: string;
};

export type AnalyticsStatusCount = {
  status: string;
  count: number;
};

export type AnalyticsMonthlySpend = CurrencyAmount & {
  month: string;
};

export type AnalyticsOverview = {
  generated_at: string;
  period_months: number;
  scope: "organization" | "managed" | "personal" | string;
  summary: {
    report_count: number;
    pending_approval_count: number;
    approved_pending_payment_count: number;
    paid_count: number;
    rejected_count: number;
    policy_violation_count: number;
    policy_violation_item_rate: number;
    average_approval_hours?: number | null;
    total_requested: CurrencyAmount[];
  };
  report_statuses: AnalyticsStatusCount[];
  spending_by_category: AnalyticsCategorySpend[];
  monthly_spend: AnalyticsMonthlySpend[];
};

export type DelegationCandidate = {
  id: string;
  full_name: string;
};

export type ApprovalDelegation = {
  id: string;
  delegator_user_id: string;
  delegate_user_id: string;
  delegate_name?: string | null;
  start_date: string;
  end_date: string;
  scope: "all" | "approval" | string;
  is_active: boolean;
  remarks?: string | null;
  created_at?: string;
  updated_at?: string;
};

export type ApprovalDelegationInput = Pick<ApprovalDelegation, "delegate_user_id" | "start_date" | "end_date" | "scope" | "remarks">;

export type PaymentStatus = "pending" | "batched" | "exported" | "paid" | "failed";

export type PaymentBatchSummary = {
  id: string;
  batch_reference: string;
  status: "created" | "exported" | string;
  currency: string;
  total_amount: number;
  payment_count: number;
  created_by?: string | null;
  created_by_name?: string | null;
  created_at?: string | null;
  exported_at?: string | null;
  remarks?: string | null;
};

export type PaymentRecord = {
  id: string;
  report_id: string;
  report_number: string;
  employee_name?: string | null;
  employee_number?: string | null;
  payment_reference: string;
  amount: number;
  currency: string;
  status: PaymentStatus | string;
  payment_date?: string | null;
  exported_at?: string | null;
  batch?: Pick<PaymentBatchSummary, "id" | "batch_reference" | "status"> | null;
  provider_reference?: string | null;
  failure_reason?: string | null;
  remarks?: string | null;
};

export type PaymentQueueResponse = {
  items: PaymentRecord[];
  total: number;
};

export type PaymentBatchListResponse = {
  items: PaymentBatchSummary[];
  total: number;
};

export type PaymentBatchCreateInput = {
  payment_ids: string[];
  remarks?: string | null;
};

export type PaymentPaidInput = {
  provider_reference: string;
  payment_date?: string | null;
  remarks?: string | null;
};

export type PaymentFailedInput = {
  failure_reason: string;
  remarks?: string | null;
};

export type PaymentCsvDownload = {
  blob: Blob;
  filename: string;
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

// Clerk manages the browser session. Keep the short-lived API token in memory
// only, so a token is never persisted in localStorage by this application.
let accessToken: string | null = null;

export function setApiToken(token: string | null) {
  accessToken = token;
}

apiClient.interceptors.request.use((config) => {
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`;
  return config;
});

const unwrap = <T>(request: Promise<{ data: T }>) => request.then((response) => response.data);

/** Return a safe, readable message for FastAPI and network errors. */
export function getApiErrorMessage(error: unknown, fallback: string) {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string" && detail.trim()) return detail;
    if (Array.isArray(detail)) {
      const messages = detail
        .map((entry) => (typeof entry === "string" ? entry : typeof entry?.msg === "string" ? entry.msg : ""))
        .filter(Boolean);
      if (messages.length > 0) return messages.join(" ");
    }
  }

  if (error instanceof Error && error.message) return error.message;
  return fallback;
}

/** Extract a stable API error code without exposing transport details to UI components. */
export function getApiErrorCode(error: unknown) {
  if (!axios.isAxiosError(error)) return undefined;
  const detail = error.response?.data?.detail;
  if (detail && typeof detail === "object" && "code" in detail && typeof detail.code === "string") {
    return detail.code;
  }
  return undefined;
}

export const policiesApi = {
  list: () => unwrap(apiClient.get<Policy[]>("/policies")),
  create: (input: PolicyInput) => unwrap(apiClient.post<Policy>("/policies", input)),
  update: (policyId: string, input: PolicyInput) => unwrap(apiClient.patch<Policy>(`/policies/${policyId}`, input)),
  activate: (policyId: string) => unwrap(apiClient.post<Policy>(`/policies/${policyId}/activate`)),
  indexAssistant: (policyId: string, content: string) =>
    unwrap(apiClient.post<PolicyAssistantIndexResponse>(`/policies/${policyId}/assistant-index`, { content })),
  askAssistant: (policyId: string, input: PolicyAssistantQuestion) =>
    unwrap(apiClient.post<PolicyAssistantAskResponse>(`/policies/${policyId}/assistant-ask`, input)),
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
  me: () => unwrap(apiClient.get<SessionUser>("/auth/me")),
};

export const usersApi = {
  list: () => unwrap(apiClient.get<ManagedUser[]>("/users")),
};

export const rolesApi = {
  list: () => unwrap(apiClient.get<WorkflowRoleOption[]>("/roles")),
};

export const categoriesApi = {
  list: () => unwrap(apiClient.get<Category[]>("/categories")),
  create: (input: CategoryInput) => unwrap(apiClient.post<Category>("/categories", input)),
  update: (categoryId: string, input: Partial<CategoryInput>) =>
    unwrap(apiClient.patch<Category>(`/categories/${categoryId}`, input)),
  remove: (categoryId: string) => unwrap(apiClient.delete<void>(`/categories/${categoryId}`)),
};

export const vendorsApi = {
  list: () => unwrap(apiClient.get<Vendor[]>("/vendors")),
};

export const workflowsApi = {
  list: () => unwrap(apiClient.get<WorkflowRule[]>("/workflows")),
  get: (workflowId: string) => unwrap(apiClient.get<WorkflowRule>(`/workflows/${workflowId}`)),
  create: (input: WorkflowRuleInput) => unwrap(apiClient.post<WorkflowRule>("/workflows", input)),
  update: (workflowId: string, input: Partial<WorkflowRuleInput>) =>
    unwrap(apiClient.patch<WorkflowRule>(`/workflows/${workflowId}`, input)),
  remove: (workflowId: string) => unwrap(apiClient.delete<void>(`/workflows/${workflowId}`)),
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
  analyzeReceipt: (reportId: string, itemId: string, attachmentId?: string) =>
    unwrap(
      apiClient.post<ReceiptAnalysisResponse>(
        `/reports/${reportId}/items/${itemId}/receipt-analysis`,
        attachmentId ? { attachment_id: attachmentId } : {},
      ),
    ),
};

function attachmentPath(url: string) {
  const baseUrl = String(apiClient.defaults.baseURL ?? "");
  const basePath = baseUrl.startsWith("http") ? new URL(baseUrl).pathname : baseUrl;
  const normalizedBasePath = basePath.replace(/\/$/, "");
  return normalizedBasePath && url.startsWith(`${normalizedBasePath}/`)
    ? url.slice(normalizedBasePath.length)
    : url;
}

export const attachmentsApi = {
  download: (url: string) => unwrap(apiClient.get<Blob>(attachmentPath(url), { responseType: "blob" })),
};

export const approvalsApi = {
  queue: () => unwrap(apiClient.get<ApprovalQueueItem[] | { queue: ApprovalQueueItem[] }>("/approvals/queue")).then((data) =>
    Array.isArray(data) ? data : data.queue ?? [],
  ),
  history: () => unwrap(apiClient.get<ApprovalQueueItem[]>("/approvals/history")),
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

export const analyticsApi = {
  overview: (periodMonths = 6) =>
    unwrap(apiClient.get<AnalyticsOverview>("/analytics/overview", { params: { period_months: periodMonths } })),
};

export const delegationsApi = {
  list: (includeInactive = false) => unwrap(apiClient.get<ApprovalDelegation[]>("/delegations", { params: includeInactive ? { include_inactive: true } : undefined })),
  candidates: () => unwrap(apiClient.get<DelegationCandidate[]>("/delegations/candidates")),
  create: (input: ApprovalDelegationInput) => unwrap(apiClient.post<ApprovalDelegation>("/delegations", input)),
  deactivate: (delegationId: string) => unwrap(apiClient.delete<ApprovalDelegation>(`/delegations/${delegationId}`)),
};

function csvFilename(contentDisposition: string | undefined, fallback: string) {
  const matchedName = contentDisposition?.match(/filename\*?=(?:UTF-8''|")?([^;"]+)/i)?.[1];
  let decodedName = fallback;
  if (matchedName) {
    try {
      decodedName = decodeURIComponent(matchedName.trim());
    } catch {
      decodedName = matchedName.trim();
    }
  }
  return decodedName.replace(/[^a-zA-Z0-9._-]/g, "_") || fallback;
}

export const paymentsApi = {
  list: (input: { status?: PaymentStatus; batchId?: string; limit?: number; offset?: number } = {}) => {
    const params: Record<string, string | number> = {};
    if (input.status) params.status = input.status;
    if (input.batchId) params.batch_id = input.batchId;
    if (input.limit !== undefined) params.limit = input.limit;
    if (input.offset !== undefined) params.offset = input.offset;
    return unwrap(apiClient.get<PaymentQueueResponse>("/payments", { params }));
  },
  listBatches: (input: { limit?: number; offset?: number } = {}) => {
    const params: Record<string, number> = {};
    if (input.limit !== undefined) params.limit = input.limit;
    if (input.offset !== undefined) params.offset = input.offset;
    return unwrap(apiClient.get<PaymentBatchListResponse>("/payments/batches", { params }));
  },
  createBatch: (input: PaymentBatchCreateInput) =>
    unwrap(apiClient.post<PaymentBatchSummary>("/payments/batches", input)),
  exportBatch: async (batchId: string): Promise<PaymentCsvDownload> => {
    const response = await apiClient.post<Blob>(`/payments/batches/${batchId}/export`, undefined, { responseType: "blob" });
    return {
      blob: response.data,
      filename: csvFilename(response.headers["content-disposition"], `payment-batch-${batchId}.csv`),
    };
  },
  markPaid: (paymentId: string, input: PaymentPaidInput) =>
    unwrap(apiClient.post<PaymentRecord>(`/payments/${paymentId}/mark-paid`, input)),
  markFailed: (paymentId: string, input: PaymentFailedInput) =>
    unwrap(apiClient.post<PaymentRecord>(`/payments/${paymentId}/mark-failed`, input)),
};

export { apiClient };
