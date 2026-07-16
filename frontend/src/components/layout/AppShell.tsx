import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Bank, ChartBar, ClipboardText, Files, GitBranch, ListChecks, SignOut, Users, UserSwitch } from "@phosphor-icons/react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import { hasPermission } from "../../auth/permissions";
import { NotificationBell } from "../../features/notifications/NotificationBell";
import { ThemeToggle } from "./ThemeToggle";

const navigation = [
  ["/reports", "Reports", "report:read", ClipboardText], ["/analytics", "Analytics", "report:read", ChartBar], ["/payments", "Payments", "payment:manage", Bank], ["/approvals", "Approvals", "report:approve", ListChecks], ["/delegations", "Delegations", "report:approve", UserSwitch], ["/policies", "Policies", "policy:manage", Files], ["/categories", "Categories", "category:manage", ListChecks], ["/workflows", "Workflows", "workflow:manage", GitBranch], ["/users", "Users", "user:read", Users], ["/org-chart", "Org chart", "user:read", GitBranch],
] as const;
export function AppShell({ children }: { children: ReactNode }) {
  const { logout, user } = useAuth(); const [mobileOpen, setMobileOpen] = useState(false); const location = useLocation();
  const items = useMemo(() => navigation.filter(([, , permission]) => hasPermission(user, permission)), [user]);
  useEffect(() => setMobileOpen(false), [location.pathname]);
  const nav = <nav className="sidebar-nav" aria-label="Primary navigation"><p>Workspace</p>{items.map(([to, label, , Icon]) => <NavLink key={to} to={to}><span><Icon aria-hidden size={18} weight="bold" /></span>{label}</NavLink>)}</nav>;
  return <div className="app-shell"><aside className={mobileOpen ? "sidebar open" : "sidebar"}><Link className="wordmark" to="/reports">Presidio<span>.</span></Link>{nav}<div className="sidebar-foot">Expense operations<br />made human.</div></aside>{mobileOpen && <button aria-label="Close navigation" className="nav-scrim" onClick={() => setMobileOpen(false)} />}
    <section className="workspace"><header className="topbar"><button aria-label="Open navigation" className="mobile-menu icon-button" onClick={() => setMobileOpen(true)}>☰</button><div className="topbar-spacer" /><span className="user-email">{user?.email}</span><ThemeToggle /><NotificationBell /><button className="signout" onClick={() => void logout()}>Sign out <SignOut aria-hidden size={17} weight="bold" /></button></header>{children}</section></div>;
}
