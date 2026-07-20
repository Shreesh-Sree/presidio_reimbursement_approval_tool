import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  Bank,
  Buildings,
  CaretLeft,
  CaretRight,
  ChartBar,
  ClipboardText,
  Files,
  GitBranch,
  List,
  ListChecks,
  SidebarSimple,
  SignOut,
  Storefront,
  Users,
  UserSwitch,
  CheckSquare,
  Plus,
  X,
} from "@phosphor-icons/react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import { hasPermission, isAdministrator } from "../../auth/permissions";
import { NotificationBell } from "../../features/notifications/NotificationBell";
import { ThemeToggle } from "./ThemeToggle";
import { RoleAwareAIChatbot } from "../ai/RoleAwareAIChatbot";

type ServiceTag = "AI" | "OCR";
type NavigationItem = {
  to: string;
  label: string;
  permission: string;
  Icon: typeof ClipboardText;
  tag?: ServiceTag;
};

const navigation: readonly NavigationItem[] = [
  { to: "/reports", label: "Reports", permission: "employee:access", Icon: ClipboardText, tag: "OCR" },
  { to: "/analytics", label: "Analytics", permission: "report:read", Icon: ChartBar },
  { to: "/payments", label: "Payments", permission: "payment:manage", Icon: Bank },
  { to: "/approvals", label: "Approvals", permission: "report:approve", Icon: ListChecks, tag: "AI" },
  { to: "/delegations", label: "Delegations", permission: "report:approve", Icon: UserSwitch },
  { to: "/policies", label: "Policies", permission: "category:read", Icon: Files, tag: "AI" },
  { to: "/categories", label: "Categories", permission: "category:manage", Icon: ListChecks },
  { to: "/workflows", label: "Workflows", permission: "workflow:manage", Icon: GitBranch },
  { to: "/vendors", label: "Vendors", permission: "vendor:manage", Icon: Storefront },
  { to: "/departments", label: "Departments", permission: "user:update", Icon: Buildings },
  { to: "/users", label: "Users", permission: "user:read", Icon: Users },
  { to: "/org-chart", label: "Org chart", permission: "user:read", Icon: GitBranch },
  { to: "/admin/access-requests", label: "Access Requests", permission: "access_request:manage", Icon: CheckSquare },
];

const sidebarStorageKey = "presidio.sidebar.collapsed";

export function AppShell({ children }: { children: ReactNode }) {
  const { logout, user } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem(sidebarStorageKey) === "true");
  const location = useLocation();

  const isAdmin = isAdministrator(user);
  const items = useMemo(() => {
    return navigation.filter((item) => {
      if (isAdmin && item.to === "/reports") return false;
      return hasPermission(user, item.permission);
    });
  }, [user, isAdmin]);

  useEffect(() => setMobileOpen(false), [location.pathname]);
  useEffect(() => localStorage.setItem(sidebarStorageKey, String(collapsed)), [collapsed]);

  const primaryRole = user?.roles?.[0] || "Employee";

  const nav = (
    <nav className="sidebar-nav" aria-label="Primary navigation">
      <p>Workspace</p>
      {items.map(({ to, label, Icon, tag }) => (
        <NavLink aria-label={collapsed ? label : undefined} key={to} title={collapsed ? label : undefined} to={to}>
          <span className="nav-icon"><Icon aria-hidden size={18} weight="bold" /></span>
          <span className="nav-label">{label}</span>
          {tag && <span className="service-tag" title={tag === "OCR" ? "Receipt intelligence service" : "AI advisory service"}>{tag}</span>}
        </NavLink>
      ))}
    </nav>
  );

  return (
    <div className={collapsed ? "app-shell sidebar-collapsed" : "app-shell"}>
      <aside className={`${mobileOpen ? "open " : ""}sidebar${collapsed ? " collapsed" : ""}`}>
        <div className="sidebar-brand">
          <Link aria-label="AlgoQX Expense Management" className="wordmark" to={isAdmin ? "/approvals" : "/reports"}>AlgoQX<span> Expense</span></Link>
          <button aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"} className="sidebar-toggle icon-button" onClick={() => setCollapsed((value) => !value)} type="button">
            {collapsed ? <CaretRight aria-hidden size={17} weight="bold" /> : <CaretLeft aria-hidden size={17} weight="bold" />}
          </button>
          <button aria-label="Close navigation" className="sidebar-close icon-button" onClick={() => setMobileOpen(false)} type="button"><X aria-hidden size={18} weight="bold" /></button>
        </div>
        {nav}
        <div className="sidebar-foot"><SidebarSimple aria-hidden size={16} weight="bold" /><span>Expense management<br />powered by AlgoQX.</span></div>
      </aside>
      {mobileOpen && <button aria-label="Close navigation" className="nav-scrim" onClick={() => setMobileOpen(false)} type="button" />}
      <section className="workspace">
        <header className="topbar">
          <button aria-label="Open navigation" className="mobile-menu icon-button" onClick={() => setMobileOpen(true)} type="button"><List aria-hidden size={21} weight="bold" /></button>
          <div className="topbar-spacer" />
          {hasPermission(user, "report:create") && (
            <Link
              to="/reports?action=new"
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-[#00ED64] text-[#001E2B] text-xs font-semibold hover:bg-[#00C956] transition-colors shadow-xs mr-3"
              title="Create New Expense Report"
            >
              <Plus size={15} weight="bold" />
              <span className="hidden sm:inline">New Report</span>
            </Link>
          )}
          <div className="topbar-user-container">
            <span className="user-email">{user?.email}</span>
            <span className={`role-badge role-${primaryRole.toLowerCase()}`}>{primaryRole.toUpperCase()}</span>
          </div>
          <ThemeToggle />
          <NotificationBell />
          <button className="signout" onClick={() => void logout()} type="button"><span>Sign out</span> <SignOut aria-hidden size={17} weight="bold" /></button>
        </header>
        {children}
      </section>
      <RoleAwareAIChatbot />
    </div>
  );
}
