import SettingsOutlinedIcon from "@mui/icons-material/SettingsOutlined";
import { Alert, Box, Paper, Typography } from "@mui/material";

/** Safe failure state for environments that have not been connected to Clerk. */
export function OAuthConfigurationPage() {
  return (
    <Box
      component="main"
      sx={{ alignItems: "center", display: "flex", justifyContent: "center", minHeight: "100vh", p: { xs: 2, sm: 4 } }}
    >
      <Paper elevation={0} sx={{ border: 1, borderColor: "divider", maxWidth: 600, p: { xs: 3, sm: 4 }, width: "100%" }}>
        <SettingsOutlinedIcon color="primary" fontSize="large" />
        <Typography component="h1" sx={{ mt: 1 }} variant="h4">OAuth sign-in is not configured</Typography>
        <Typography color="text.secondary" sx={{ mt: 1 }}>
          This deployment only supports Clerk OAuth. Add the public Clerk publishable key before serving the application.
        </Typography>
        <Alert severity="info" sx={{ mt: 3 }}>
          Set <code>VITE_CLERK_PUBLISHABLE_KEY</code> and, if your Clerk JWT template uses a different name, <code>VITE_CLERK_JWT_TEMPLATE</code>. Do not place Clerk secret keys in the frontend.
        </Alert>
      </Paper>
    </Box>
  );
}
