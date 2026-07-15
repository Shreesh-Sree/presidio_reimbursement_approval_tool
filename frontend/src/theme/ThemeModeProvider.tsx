/* oxlint-disable react/only-export-components */
import { CssBaseline, ThemeProvider } from "@mui/material";
import type { PaletteMode } from "@mui/material";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { createAppTheme } from "./appTheme";

export type ThemePreference = PaletteMode | "system";

type ThemeModeContextValue = {
  mode: ThemePreference;
  resolvedMode: PaletteMode;
  setMode: (mode: ThemePreference) => void;
};

const THEME_STORAGE_KEY = "presidio-color-scheme";
const ThemeModeContext = createContext<ThemeModeContextValue | undefined>(undefined);

function systemMode(): PaletteMode {
  if (typeof window === "undefined" || !window.matchMedia) return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function savedMode(): ThemePreference {
  if (typeof window === "undefined") return "system";
  try {
    const storedMode = window.localStorage.getItem(THEME_STORAGE_KEY);
    return storedMode === "light" || storedMode === "dark" || storedMode === "system" ? storedMode : "system";
  } catch {
    return "system";
  }
}

export function ThemeModeProvider({ children }: { children: ReactNode }) {
  const [mode, setStoredMode] = useState<ThemePreference>(savedMode);
  const [preferredSystemMode, setPreferredSystemMode] = useState<PaletteMode>(systemMode);
  const resolvedMode = mode === "system" ? preferredSystemMode : mode;
  const theme = useMemo(() => createAppTheme(resolvedMode), [resolvedMode]);

  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return undefined;
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const updateSystemMode = (event: MediaQueryListEvent) => setPreferredSystemMode(event.matches ? "dark" : "light");
    mediaQuery.addEventListener("change", updateSystemMode);
    return () => mediaQuery.removeEventListener("change", updateSystemMode);
  }, []);

  useEffect(() => {
    const documentElement = document.documentElement;
    documentElement.classList.toggle("dark", resolvedMode === "dark");
    documentElement.dataset.theme = resolvedMode;
    documentElement.style.colorScheme = resolvedMode;
  }, [resolvedMode]);

  const setMode = useCallback((nextMode: ThemePreference) => {
    setStoredMode(nextMode);
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, nextMode);
    } catch {
      // The app remains usable when browser storage is disabled.
    }
  }, []);

  const value = useMemo<ThemeModeContextValue>(() => ({ mode, resolvedMode, setMode }), [mode, resolvedMode, setMode]);

  return (
    <ThemeModeContext.Provider value={value}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </ThemeModeContext.Provider>
  );
}

export function useThemeMode() {
  const context = useContext(ThemeModeContext);
  if (!context) throw new Error("useThemeMode must be used inside ThemeModeProvider");
  return context;
}
