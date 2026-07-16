/* oxlint-disable react/only-export-components */
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

export type ThemePreference = "light" | "dark" | "system";
type ThemeModeContextValue = { mode: ThemePreference; resolvedMode: "light" | "dark"; setMode: (mode: ThemePreference) => void };
const ThemeModeContext = createContext<ThemeModeContextValue | null>(null);

function mediaQuery() { return typeof window.matchMedia === "function" ? window.matchMedia("(prefers-color-scheme: dark)") : null; }
function systemMode() { return mediaQuery()?.matches ? "dark" : "light"; }

export function ThemeModeProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<ThemePreference>(() => (localStorage.getItem("presidio-theme") as ThemePreference) || "light");
  const [resolvedMode, setResolvedMode] = useState<"light" | "dark">(() => mode === "system" ? systemMode() : mode);
  useEffect(() => {
    const apply = () => setResolvedMode(mode === "system" ? systemMode() : mode);
    apply(); localStorage.setItem("presidio-theme", mode);
    const media = mediaQuery(); media?.addEventListener("change", apply);
    return () => media?.removeEventListener("change", apply);
  }, [mode]);
  useEffect(() => {
    document.documentElement.classList.toggle("dark", resolvedMode === "dark");
    document.documentElement.dataset.theme = resolvedMode;
    localStorage.setItem("presidio-color-scheme", resolvedMode);
  }, [resolvedMode]);
  const value = useMemo(() => ({ mode, resolvedMode, setMode }), [mode, resolvedMode]);
  return <ThemeModeContext.Provider value={value}>{children}</ThemeModeContext.Provider>;
}
export function useThemeMode() { const value = useContext(ThemeModeContext); if (!value) throw new Error("useThemeMode must be used inside ThemeModeProvider"); return value; }
