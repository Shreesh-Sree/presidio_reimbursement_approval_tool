import { useState } from "react";
import { useThemeMode, type ThemePreference } from "../../theme/ThemeModeProvider";

export function ThemeToggle() {
  const { mode, resolvedMode, setMode } = useThemeMode(); const [open, setOpen] = useState(false);
  const choices: Array<[ThemePreference, string]> = [["light", "Light"], ["dark", "Dark"], ["system", "System"]];
  return <div className="theme-toggle"><button aria-expanded={open} aria-label="Change color theme" className="icon-button" onClick={() => setOpen(!open)}>{resolvedMode === "dark" ? "◐" : "☼"}</button>{open && <div className="theme-menu">{choices.map(([value, label]) => <button className={mode === value ? "active" : ""} key={value} onClick={() => { setMode(value); setOpen(false); }}>{label}</button>)}</div>}</div>;
}
