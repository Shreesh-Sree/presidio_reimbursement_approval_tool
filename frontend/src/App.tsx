import { BrowserRouter, Routes, Route, Navigate, Link } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { RequirePermission } from "./auth/RequirePermission";
import { LoginPage } from "./features/auth/LoginPage";
import { ApprovalQueuePage } from "./features/approvals/ApprovalQueuePage";
import { ReportReview } from "./features/approvals/ReportReview";
import { CategoriesPage } from "./features/categories/CategoriesPage";
import { PoliciesPage } from "./features/policies/PoliciesPage";
import { ReportEditor } from "./features/reports/ReportEditor";
import { ReportsListPage } from "./features/reports/ReportsListPage";
import { NotificationBell } from "./features/notifications/NotificationBell";
import { UsersPage } from "./features/users/UsersPage";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token, user } = useAuth();
  if (!token) return <Navigate to="/login" />;

  return (
    <>
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 px-4 py-3 backdrop-blur dark:border-slate-800 dark:bg-slate-950/95 sm:px-6">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3">
          <Link className="font-semibold text-slate-950 dark:text-white" to="/reports">Presidio reimbursements</Link>
          <nav aria-label="Primary navigation" className="order-3 flex w-full gap-1 overflow-x-auto text-sm sm:order-2 sm:w-auto">
            <Link className="rounded-md px-2 py-1.5 text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800" to="/reports">Reports</Link>
            <Link className="rounded-md px-2 py-1.5 text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800" to="/approvals">Approvals</Link>
            <Link className="rounded-md px-2 py-1.5 text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800" to="/policies">Policies</Link>
            <Link className="rounded-md px-2 py-1.5 text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800" to="/categories">Categories</Link>
          </nav>
          <div className="flex items-center gap-2">
            <span className="hidden max-w-40 truncate text-sm text-slate-600 dark:text-slate-300 sm:block">{user?.email}</span>
            <NotificationBell />
          </div>
        </div>
      </header>
      {children}
    </>
  );
}

function AppContent() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/users" element={<ProtectedRoute><UsersPage /></ProtectedRoute>} />
      <Route path="/policies" element={<ProtectedRoute><RequirePermission permission="policy:manage"><PoliciesPage /></RequirePermission></ProtectedRoute>} />
      <Route path="/categories" element={<ProtectedRoute><RequirePermission permission="category:manage"><CategoriesPage /></RequirePermission></ProtectedRoute>} />
      <Route path="/reports" element={<ProtectedRoute><RequirePermission permission="report:read"><ReportsListPage /></RequirePermission></ProtectedRoute>} />
      <Route path="/reports/:reportId" element={<ProtectedRoute><RequirePermission permission="report:read"><ReportEditor /></RequirePermission></ProtectedRoute>} />
      <Route path="/approvals" element={<ProtectedRoute><RequirePermission permission="report:approve"><ApprovalQueuePage /></RequirePermission></ProtectedRoute>} />
      <Route path="/approvals/:reportId" element={<ProtectedRoute><RequirePermission permission="report:approve"><ReportReview /></RequirePermission></ProtectedRoute>} />
      <Route path="/" element={<Navigate to="/reports" />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppContent />
      </BrowserRouter>
    </AuthProvider>
  );
}
