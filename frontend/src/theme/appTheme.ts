import { createTheme } from "@mui/material/styles";
import type { PaletteMode } from "@mui/material";

const brand = {
  blue: "#4057d6",
  blueDark: "#7287ff",
  teal: "#007c78",
  tealDark: "#56d8d1",
};

/**
 * The application palette is deliberately kept in one place so every MUI
 * component receives the same light and dark treatment.
 */
export function createAppTheme(mode: PaletteMode) {
  const isDark = mode === "dark";

  return createTheme({
    palette: {
      mode,
      primary: {
        main: isDark ? brand.blueDark : brand.blue,
        contrastText: "#ffffff",
      },
      secondary: {
        main: isDark ? brand.tealDark : brand.teal,
      },
      background: {
        default: isDark ? "#10131c" : "#f6f7fb",
        paper: isDark ? "#191d28" : "#ffffff",
      },
      divider: isDark ? "rgba(226, 232, 240, 0.14)" : "rgba(15, 23, 42, 0.12)",
      text: {
        primary: isDark ? "#f4f6fb" : "#172033",
        secondary: isDark ? "#c2cadb" : "#5a657a",
      },
      success: { main: isDark ? "#58c98a" : "#16834a" },
      warning: { main: isDark ? "#f9bc63" : "#a85d00" },
      error: { main: isDark ? "#ff8a91" : "#ba1a1a" },
      info: { main: isDark ? "#8db4ff" : "#2457ad" },
    },
    shape: { borderRadius: 12 },
    typography: {
      fontFamily: 'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
      h1: { fontWeight: 700, letterSpacing: "-0.025em" },
      h2: { fontWeight: 700, letterSpacing: "-0.02em" },
      button: { fontWeight: 650, textTransform: "none" },
    },
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          body: {
            minWidth: 320,
          },
          "*:focus-visible": {
            outline: `3px solid ${isDark ? "#aab6ff" : "#4057d6"}`,
            outlineOffset: 2,
          },
        },
      },
      MuiAppBar: {
        styleOverrides: {
          root: {
            backgroundImage: "none",
            boxShadow: isDark ? "0 1px 0 rgba(226, 232, 240, 0.12)" : "0 1px 0 rgba(15, 23, 42, 0.10)",
          },
        },
      },
      MuiButton: {
        styleOverrides: {
          root: { borderRadius: 10 },
          contained: { boxShadow: "none" },
        },
      },
      MuiDrawer: {
        styleOverrides: {
          paper: {
            backgroundImage: "none",
            borderRight: `1px solid ${isDark ? "rgba(226, 232, 240, 0.14)" : "rgba(15, 23, 42, 0.10)"}`,
          },
        },
      },
      MuiPaper: {
        defaultProps: { elevation: 0 },
        styleOverrides: {
          root: {
            backgroundImage: "none",
          },
        },
      },
      MuiCard: {
        styleOverrides: {
          root: {
            border: `1px solid ${isDark ? "rgba(226, 232, 240, 0.14)" : "rgba(15, 23, 42, 0.10)"}`,
            boxShadow: isDark ? "0 10px 25px rgba(0, 0, 0, 0.16)" : "0 8px 24px rgba(15, 23, 42, 0.06)",
          },
        },
      },
      MuiOutlinedInput: {
        styleOverrides: {
          root: {
            backgroundColor: isDark ? "rgba(255, 255, 255, 0.02)" : "#ffffff",
          },
        },
      },
    },
  });
}
