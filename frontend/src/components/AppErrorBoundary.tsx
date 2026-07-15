import RefreshOutlinedIcon from "@mui/icons-material/RefreshOutlined";
import { Alert, Box, Button, Container, Stack, Typography } from "@mui/material";
import { Component } from "react";
import type { ErrorInfo, ReactNode } from "react";

type AppErrorBoundaryProps = {
  children: ReactNode;
};

type AppErrorBoundaryState = {
  hasError: boolean;
};

/** A route-level fallback so a rendering error does not leave users with a blank screen. */
export class AppErrorBoundary extends Component<AppErrorBoundaryProps, AppErrorBoundaryState> {
  state: AppErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): AppErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(_error: Error, _errorInfo: ErrorInfo) {
    // Logging is intentionally delegated to the application's configured monitoring layer.
  }

  render() {
    if (!this.state.hasError) return this.props.children;

    return (
      <Box component="main" sx={{ display: "grid", minHeight: "100vh", placeItems: "center", p: 3 }}>
        <Container maxWidth="sm">
          <Stack spacing={2.5}>
            <Typography component="h1" variant="h4">Something went wrong</Typography>
            <Alert severity="error">This screen could not be displayed. Your saved data has not been changed.</Alert>
            <Typography color="text.secondary">Try again. If the issue continues, return to the reports page or contact your administrator.</Typography>
            <Box>
              <Button onClick={() => this.setState({ hasError: false })} startIcon={<RefreshOutlinedIcon />} variant="contained">
                Try again
              </Button>
            </Box>
          </Stack>
        </Container>
      </Box>
    );
  }
}
