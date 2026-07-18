import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  Bank,
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
  X,
} from "@phosphor-icons/react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import { hasPermission } from "../../auth/permissions";
import { NotificationBell } from "../../features/notifications/NotificationBell";
import { ThemeToggle } from "./ThemeToggle";

type ServiceTag = "AI" | "OCR";
type NavigationItem = {
  to: string;
  label: string;
  permission: string;
  Icon: typeof ClipboardText;
  tag?: ServiceTag;
};

const navigation: readonly NavigationItem[] = [
  { to: "/reports", label: "Reports", permission: "report:read", Icon: ClipboardText, tag: "OCR" },
  { to: "/analytics", label: "Analytics", permission: "report:read", Icon: ChartBar },
  { to: "/payments", label: "Payments", permission: "payment:manage", Icon: Bank },
  { to: "/approvals", label: "Approvals", permission: "report:approve", Icon: ListChecks, tag: "AI" },
  { to: "/delegations", label: "Delegations", permission: "report:approve", Icon: UserSwitch },
  { to: "/policies", label: "Policies", permission: "policy:manage", Icon: Files, tag: "AI" },
  { to: "/categories", label: "Categories", permission: "category:manage", Icon: ListChecks },
  { to: "/workflows", label: "Workflows", permission: "workflow:manage", Icon: GitBranch },
  { to: "/vendors", label: "Vendors", permission: "vendor:manage", Icon: Storefront },
  { to: "/users", label: "Users", permission: "user:read", Icon: Users },
  { to: "/org-chart", label: "Org chart", permission: "user:read", Icon: GitBranch },
  { to: "/admin/access-requests", label: "Access Requests", permission: "user:manage", Icon: CheckSquare },
];

const sidebarStorageKey = "presidio.sidebar.collapsed";

export function AppShell({ children }: { children: ReactNode }) {
  const { logout, user } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem(sidebarStorageKey) === "true");
  const location = useLocation();
  const items = useMemo(() => navigation.filter((item) => hasPermission(user, item.permission)), [user]);

  useEffect(() => setMobileOpen(false), [location.pathname]);
  useEffect(() => localStorage.setItem(sidebarStorageKey, String(collapsed)), [collapsed]);

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
          <Link aria-label="AlgoQX Expense Management" className="wordmark" to="/reports">AlgoQX<span> Expense</span></Link>
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
          <span className="user-email">{user?.email}</span>
          <ThemeToggle />
          <NotificationBell />
          <button className="signout" onClick={() => void logout()} type="button"><span>Sign out</span> <SignOut aria-hidden size={17} weight="bold" /></button>
        </header>
        {children}
      </section>
    </div>
  );
}
