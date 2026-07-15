import AccountTreeOutlinedIcon from "@mui/icons-material/AccountTreeOutlined";
import BarChartOutlinedIcon from "@mui/icons-material/BarChartOutlined";
import CategoryOutlinedIcon from "@mui/icons-material/CategoryOutlined";
import FactCheckOutlinedIcon from "@mui/icons-material/FactCheckOutlined";
import GroupAddOutlinedIcon from "@mui/icons-material/GroupAddOutlined";
import LogoutOutlinedIcon from "@mui/icons-material/LogoutOutlined";
import MenuIcon from "@mui/icons-material/Menu";
import PeopleAltOutlinedIcon from "@mui/icons-material/PeopleAltOutlined";
import PaymentsOutlinedIcon from "@mui/icons-material/PaymentsOutlined";
import PolicyOutlinedIcon from "@mui/icons-material/PolicyOutlined";
import ReceiptLongOutlinedIcon from "@mui/icons-material/ReceiptLongOutlined";
import {
  AppBar,
  Box,
  Button,
  Divider,
  Drawer,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Tooltip,
  Typography,
  useMediaQuery,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { Link as RouterLink, NavLink, useLocation } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import { hasPermission } from "../../auth/permissions";
import { NotificationBell } from "../../features/notifications/NotificationBell";
import { ThemeToggle } from "./ThemeToggle";

const drawerWidth = 272;

type NavigationItem = {
  label: string;
  permission: string;
  to: string;
  icon: ReactNode;
};

const navigation: NavigationItem[] = [
  { to: "/reports", label: "Reports", permission: "report:read", icon: <ReceiptLongOutlinedIcon /> },
  { to: "/analytics", label: "Analytics", permission: "report:read", icon: <BarChartOutlinedIcon /> },
  { to: "/payments", label: "Payments", permission: "payment:manage", icon: <PaymentsOutlinedIcon /> },
  { to: "/approvals", label: "Approvals", permission: "report:approve", icon: <FactCheckOutlinedIcon /> },
  { to: "/delegations", label: "Delegations", permission: "report:approve", icon: <GroupAddOutlinedIcon /> },
  { to: "/policies", label: "Policies", permission: "policy:manage", icon: <PolicyOutlinedIcon /> },
  { to: "/categories", label: "Categories", permission: "category:manage", icon: <CategoryOutlinedIcon /> },
  { to: "/workflows", label: "Workflows", permission: "workflow:manage", icon: <AccountTreeOutlinedIcon /> },
  { to: "/users", label: "Users", permission: "user:read", icon: <PeopleAltOutlinedIcon /> },
  { to: "/org-chart", label: "Org chart", permission: "user:read", icon: <AccountTreeOutlinedIcon /> },
];

type AppShellProps = {
  children: ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  const { logout, user } = useAuth();
  const location = useLocation();
  const theme = useTheme();
  const isDesktop = useMediaQuery(theme.breakpoints.up("md"), { noSsr: true });
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);
  const visibleNavigation = useMemo(
    () => navigation.filter((item) => hasPermission(user, item.permission)),
    [user],
  );

  useEffect(() => {
    setMobileDrawerOpen(false);
  }, [location.pathname]);

  const drawerContent = (
    <>
      <Toolbar sx={{ minHeight: "72px !important", px: 3 }}>
        <Typography color="text.primary" component={RouterLink} sx={{ fontSize: "1rem", fontWeight: 800, textDecoration: "none" }} to="/reports">
          Presidio reimbursements
        </Typography>
      </Toolbar>
      <Divider />
      <List aria-label="Primary navigation" sx={{ px: 1.25, py: 1.5 }}>
        {visibleNavigation.map((item) => {
          const selected = location.pathname === item.to || location.pathname.startsWith(`${item.to}/`);
          return (
            <ListItemButton
              component={NavLink}
              key={item.to}
              onClick={() => setMobileDrawerOpen(false)}
              selected={selected}
              sx={{ borderRadius: 2, mb: 0.5, minHeight: 46 }}
              to={item.to}
            >
              <ListItemIcon sx={{ color: selected ? "primary.main" : "text.secondary", minWidth: 38 }}>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} primaryTypographyProps={{ fontWeight: selected ? 700 : 550 }} />
            </ListItemButton>
          );
        })}
      </List>
    </>
  );

  return (
    <Box sx={{ display: "flex", minHeight: "100vh" }}>
      <AppBar
        color="inherit"
        position="fixed"
        sx={{
          ml: { md: `${drawerWidth}px` },
          width: { md: `calc(100% - ${drawerWidth}px)` },
          zIndex: (currentTheme) => currentTheme.zIndex.drawer + 1,
        }}
      >
        <Toolbar sx={{ gap: 1, minHeight: "72px !important", px: { xs: 1.5, sm: 3 } }}>
          <IconButton
            aria-label="Open navigation"
            color="inherit"
            edge="start"
            onClick={() => setMobileDrawerOpen(true)}
            sx={{ display: { md: "none" }, mr: 0.5 }}
          >
            <MenuIcon />
          </IconButton>
          <Typography component={RouterLink} noWrap sx={{ color: "text.primary", display: { md: "none" }, fontSize: "0.95rem", fontWeight: 800, textDecoration: "none" }} to="/reports">
            Presidio reimbursements
          </Typography>
          <Box sx={{ flexGrow: 1 }} />
          <Typography color="text.secondary" noWrap sx={{ display: { xs: "none", sm: "block" }, maxWidth: 240, typography: "body2" }}>
            {user?.email}
          </Typography>
          <ThemeToggle />
          <NotificationBell />
          <Tooltip title="Sign out">
            <Button
              aria-label="Sign out"
              color="inherit"
              onClick={logout}
              startIcon={<LogoutOutlinedIcon />}
              sx={{ display: { xs: "none", sm: "inline-flex" } }}
              variant="text"
            >
              Sign out
            </Button>
          </Tooltip>
          <Tooltip title="Sign out">
            <IconButton aria-label="Sign out" color="inherit" onClick={logout} sx={{ display: { sm: "none" } }}>
              <LogoutOutlinedIcon />
            </IconButton>
          </Tooltip>
        </Toolbar>
      </AppBar>

      <Box component="nav" sx={{ flexShrink: { md: 0 }, width: { md: drawerWidth } }}>
        <Drawer
          ModalProps={{ keepMounted: true }}
          onClose={() => setMobileDrawerOpen(false)}
          open={mobileDrawerOpen}
          slotProps={{ paper: { sx: { width: drawerWidth } } }}
          sx={{ display: { md: "none" } }}
          variant="temporary"
        >
          {drawerContent}
        </Drawer>
        {isDesktop && (
          <Drawer
            open
            slotProps={{ paper: { sx: { boxSizing: "border-box", width: drawerWidth } } }}
            sx={{ display: { xs: "none", md: "block" }, "& .MuiDrawer-paper": { width: drawerWidth } }}
            variant="permanent"
          >
            {drawerContent}
          </Drawer>
        )}
      </Box>

      <Box component="div" sx={{ flexGrow: 1, minWidth: 0, width: { md: `calc(100% - ${drawerWidth}px)` } }}>
        <Toolbar sx={{ minHeight: "72px !important" }} />
        {children}
      </Box>
    </Box>
  );
}
