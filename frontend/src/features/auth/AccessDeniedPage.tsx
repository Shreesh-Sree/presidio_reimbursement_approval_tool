import LogoutOutlinedIcon from "@mui/icons-material/LogoutOutlined";
import { Alert, Box, Button, Paper, Typography } from "@mui/material";
import { useAuth } from "../../auth/AuthContext";

/** Shown only after Clerk confirms identity but the app allowlist rejects it. */
export function AccessDeniedPage() {
  const { logout, user } = useAuth();

  return (
    <Box
      component="main"
      sx={{ alignItems: "center", display: "flex", justifyContent: "center", minHeight: "100vh", p: { xs: 2, sm: 4 } }}
    >
      <Paper elevation={0} sx={{ border: 1, borderColor: "divider", maxWidth: 560, p: { xs: 3, sm: 4 }, width: "100%" }}>
        <Typography color="primary" fontWeight={800} variant="overline">Presidio reimbursements</Typography>
        <Typography component="h1" sx={{ mt: 0.5 }} variant="h4">You don’t have access yet</Typography>
        <Alert severity="warning" sx={{ mt: 2 }}>
          Your signed-in work account{user?.email ? ` (${user.email})` : ""} is not on this organization’s reimbursement allowlist.
        </Alert>
        <Typography color="text.secondary" sx={{ mt: 2 }}>
          Ask an administrator to add your email, assign your roles, and set your reporting manager. Then sign in again with the same approved OAuth account.
        </Typography>
        <Button onClick={() => void logout()} startIcon={<LogoutOutlinedIcon />} sx={{ mt: 3 }} variant="contained">
          Sign out
        </Button>
      </Paper>
    </Box>
  );
}
