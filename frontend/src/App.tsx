import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { lazy, Suspense } from "react";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { RequirePermission } from "./auth/RequirePermission";
import { AppErrorBoundary } from "./components/AppErrorBoundary";
import { BootstrapPage } from "./features/auth/BootstrapPage";
import { LoginPage } from "./features/auth/LoginPage";

const AppShell = lazy(async () => {
  const module = await import("./components/layout/AppShell");
  return { default: module.AppShell };
});

const UsersPage = lazy(async () => {
  const module = await import("./features/users/UsersPage");
  return { default: module.UsersPage };
});

const OrgChartPage = lazy(async () => {
  const module = await import("./features/users/OrgChartPage");
  return { default: module.OrgChartPage };
});

const PoliciesPage = lazy(async () => {
  const module = await import("./features/policies/PoliciesPage");
  return { default: module.PoliciesPage };
});

const CategoriesPage = lazy(async () => {
  const module = await import("./features/categories/CategoriesPage");
  return { default: module.CategoriesPage };
});

const WorkflowRulesPage = lazy(async () => {
  const module = await import("./features/workflows/WorkflowRulesPage");
  return { default: module.WorkflowRulesPage };
});

const ReportsListPage = lazy(async () => {
  const module = await import("./features/reports/ReportsListPage");
  return { default: module.ReportsListPage };
});

const ReportEditor = lazy(async () => {
  const module = await import("./features/reports/ReportEditor");
  return { default: module.ReportEditor };
});

const ApprovalQueuePage = lazy(async () => {
  const module = await import("./features/approvals/ApprovalQueuePage");
  return { default: module.ApprovalQueuePage };
});

const ReportReview = lazy(async () => {
  const module = await import("./features/approvals/ReportReview");
  return { default: module.ReportReview };
});

const DelegationsPage = lazy(async () => {
  const module = await import("./features/delegations/DelegationsPage");
  return { default: module.DelegationsPage };
});

const AnalyticsPage = lazy(async () => {
  const module = await import("./features/analytics/AnalyticsPage");
  return { default: module.AnalyticsPage };
});

const PaymentsPage = lazy(async () => {
  const module = await import("./features/payments/PaymentsPage");
  return { default: module.PaymentsPage };
});

function RouteLoading() {
  return <main className="p-6 text-sm text-slate-600 dark:text-slate-300">Loading page…</main>;
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token } = useAuth();
  if (!token) return <Navigate replace to="/login" />;
  return <Suspense fallback={<RouteLoading />}><AppShell>{children}</AppShell></Suspense>;
}

function AppContent() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/bootstrap" element={<BootstrapPage />} />
      <Route path="/users" element={<ProtectedRoute><RequirePermission permission="user:read"><UsersPage /></RequirePermission></ProtectedRoute>} />
      <Route path="/org-chart" element={<ProtectedRoute><RequirePermission permission="user:read"><OrgChartPage /></RequirePermission></ProtectedRoute>} />
      <Route path="/policies" element={<ProtectedRoute><RequirePermission permission="policy:manage"><PoliciesPage /></RequirePermission></ProtectedRoute>} />
      <Route path="/categories" element={<ProtectedRoute><RequirePermission permission="category:manage"><CategoriesPage /></RequirePermission></ProtectedRoute>} />
      <Route path="/workflows" element={<ProtectedRoute><RequirePermission permission="workflow:manage"><WorkflowRulesPage /></RequirePermission></ProtectedRoute>} />
      <Route path="/reports" element={<ProtectedRoute><RequirePermission permission="report:read"><ReportsListPage /></RequirePermission></ProtectedRoute>} />
      <Route path="/analytics" element={<ProtectedRoute><RequirePermission permission="report:read"><AnalyticsPage /></RequirePermission></ProtectedRoute>} />
      <Route path="/payments" element={<ProtectedRoute><RequirePermission permission="payment:manage"><PaymentsPage /></RequirePermission></ProtectedRoute>} />
      <Route path="/reports/:reportId" element={<ProtectedRoute><RequirePermission permission="report:read"><ReportEditor /></RequirePermission></ProtectedRoute>} />
      <Route path="/approvals" element={<ProtectedRoute><RequirePermission permission="report:approve"><ApprovalQueuePage /></RequirePermission></ProtectedRoute>} />
      <Route path="/delegations" element={<ProtectedRoute><RequirePermission permission="report:approve"><DelegationsPage /></RequirePermission></ProtectedRoute>} />
      <Route path="/approvals/:reportId" element={<ProtectedRoute><RequirePermission permission="report:approve"><ReportReview /></RequirePermission></ProtectedRoute>} />
      <Route path="/" element={<Navigate to="/reports" />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppErrorBoundary>
          <AppContent />
        </AppErrorBoundary>
      </BrowserRouter>
    </AuthProvider>
  );
}
