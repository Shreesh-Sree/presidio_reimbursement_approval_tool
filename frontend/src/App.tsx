import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { lazy, Suspense } from "react";
import type { ReactNode } from "react";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { RequirePermission } from "./auth/RequirePermission";
import { AppErrorBoundary } from "./components/AppErrorBoundary";
import { AccessDeniedPage } from "./features/auth/AccessDeniedPage";
import { OAuthConfigurationPage } from "./features/auth/OAuthConfigurationPage";
import { SignInPage } from "./features/auth/SignInPage";
import { LumaSpin } from "./components/ui/luma-spin";

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
  return <main className="route-loading"><LumaSpin label="Loading workspace" /><p>Preparing your workspace…</p></main>;
}

function AuthenticationErrorPage({ message }: { message: string }) {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-xl items-center p-6">
      <div className="w-full rounded-xl border border-orange-200 bg-orange-50 p-6 text-center dark:border-orange-950 dark:bg-orange-950/30">
        <h1 className="text-lg font-semibold text-orange-950 dark:text-orange-100">We could not verify your access</h1>
        <p className="mt-2 text-sm text-orange-800 dark:text-orange-200">{message}</p>
      </div>
    </main>
  );
}

function SignInRoute() {
  const { accessDenied, error, isLoading, status, user } = useAuth();

  if (status === "configuration_missing") return <Navigate replace to="/oauth-configuration" />;
  if (isLoading) return <RouteLoading />;
  if (accessDenied) return <Navigate replace to="/access-denied" />;
  if (status === "authorized" && user) return <Navigate replace to="/reports" />;
  if (error) return <AuthenticationErrorPage message={error} />;
  return <SignInPage />;
}

function ProtectedRoute({ children }: { children: ReactNode }) {
  const { accessDenied, error, isLoading, status, user } = useAuth();
  const location = useLocation();

  if (status === "configuration_missing") return <Navigate replace to="/oauth-configuration" />;
  if (isLoading) return <RouteLoading />;
  if (accessDenied) return <Navigate replace to="/access-denied" />;
  if (error) return <AuthenticationErrorPage message={error} />;
  if (!user) return <Navigate replace state={{ from: location }} to="/sign-in" />;
  return <Suspense fallback={<RouteLoading />}><AppShell>{children}</AppShell></Suspense>;
}

function AppContent() {
  const { status } = useAuth();

  if (status === "configuration_missing") return <OAuthConfigurationPage />;

  return (
    <Routes>
      {/* Clerk completes OAuth on a nested callback path such as
          /sign-in/sso-callback. Keep that route inside the sign-in surface so
          React Router does not send it through the catch-all redirect first. */}
      <Route path="/sign-in/*" element={<SignInRoute />} />
      <Route path="/login" element={<Navigate replace to="/sign-in" />} />
      <Route path="/bootstrap" element={<Navigate replace to="/sign-in" />} />
      <Route path="/access-denied" element={<AccessDeniedPage />} />
      <Route path="/oauth-configuration" element={<OAuthConfigurationPage />} />
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
      <Route path="*" element={<Navigate replace to="/reports" />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppErrorBoundary>
        <AppContent />
      </AppErrorBoundary>
    </AuthProvider>
  );
}
