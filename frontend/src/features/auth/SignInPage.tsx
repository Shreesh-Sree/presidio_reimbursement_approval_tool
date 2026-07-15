import { SignIn } from "@clerk/clerk-react";
import { Box, Paper, Typography } from "@mui/material";

/**
 * The available identity providers are configured in Clerk. This application
 * deliberately does not render an email/password or self-registration form.
 */
export function SignInPage() {
  return (
    <Box
      component="main"
      sx={{ alignItems: "center", display: "flex", justifyContent: "center", minHeight: "100vh", p: { xs: 2, sm: 4 } }}
    >
      <Paper elevation={0} sx={{ border: 1, borderColor: "divider", maxWidth: 480, p: { xs: 2.5, sm: 4 }, width: "100%" }}>
        <Typography color="primary" fontWeight={800} variant="overline">Presidio reimbursements</Typography>
        <Typography component="h1" sx={{ mt: 0.5 }} variant="h4">Sign in with your work account</Typography>
        <Typography color="text.secondary" sx={{ mb: 3, mt: 1 }}>
          Continue through your organization’s approved OAuth provider. Access is granted only after your work email is allowlisted by an administrator.
        </Typography>
        <Box sx={{ display: "flex", justifyContent: "center", overflowX: "auto" }}>
          <SignIn fallbackRedirectUrl="/reports" path="/sign-in" routing="path" />
        </Box>
      </Paper>
    </Box>
  );
}
