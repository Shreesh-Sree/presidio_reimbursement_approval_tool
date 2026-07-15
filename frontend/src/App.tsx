import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { RequirePermission } from "./auth/RequirePermission";
import { LoginPage } from "./features/auth/LoginPage";
import { ApprovalQueuePage } from "./features/approvals/ApprovalQueuePage";
import { ReportReview } from "./features/approvals/ReportReview";
import { CategoriesPage } from "./features/categories/CategoriesPage";
import { PoliciesPage } from "./features/policies/PoliciesPage";
import { ReportEditor } from "./features/reports/ReportEditor";
import { ReportsListPage } from "./features/reports/ReportsListPage";
import { UsersPage } from "./features/users/UsersPage";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token } = useAuth();
  return token ? <>{children}</> : <Navigate to="/login" />;
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
