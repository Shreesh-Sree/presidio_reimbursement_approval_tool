import { useState } from "react";
import { Desktop, Moon, Sun } from "@phosphor-icons/react";
import { useThemeMode, type ThemePreference } from "../../theme/ThemeModeProvider";

export function ThemeToggle() {
  const { mode, resolvedMode, setMode } = useThemeMode(); const [open, setOpen] = useState(false);
  const choices: Array<[ThemePreference, string]> = [["light", "Light"], ["dark", "Dark"], ["system", "System"]];
  const ThemeIcon = resolvedMode === "dark" ? Moon : Sun;
  const icons = { light: Sun, dark: Moon, system: Desktop };
  return <div className="theme-toggle"><button aria-expanded={open} aria-label="Change color theme" className="icon-button" onClick={() => setOpen(!open)} type="button"><ThemeIcon aria-hidden size={18} weight="bold" /></button>{open && <div className="theme-menu">{choices.map(([value, label]) => { const Icon = icons[value]; return <button className={mode === value ? "active" : ""} key={value} onClick={() => { setMode(value); setOpen(false); }} type="button"><Icon aria-hidden size={15} weight="bold" />{label}</button>; })}</div>}</div>;
}
