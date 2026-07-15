import DarkModeOutlinedIcon from "@mui/icons-material/DarkModeOutlined";
import LightModeOutlinedIcon from "@mui/icons-material/LightModeOutlined";
import SettingsBrightnessOutlinedIcon from "@mui/icons-material/SettingsBrightnessOutlined";
import { IconButton, ListItemIcon, ListItemText, Menu, MenuItem, Tooltip } from "@mui/material";
import { useState } from "react";
import type { MouseEvent } from "react";
import { type ThemePreference, useThemeMode } from "../../theme/ThemeModeProvider";

const themeChoices: Array<{ value: ThemePreference; label: string }> = [
  { value: "system", label: "Use system setting" },
  { value: "light", label: "Use light theme" },
  { value: "dark", label: "Use dark theme" },
];

function choiceIcon(mode: ThemePreference) {
  if (mode === "light") return <LightModeOutlinedIcon fontSize="small" />;
  if (mode === "dark") return <DarkModeOutlinedIcon fontSize="small" />;
  return <SettingsBrightnessOutlinedIcon fontSize="small" />;
}

export function ThemeToggle() {
  const { mode, resolvedMode, setMode } = useThemeMode();
  const [anchorElement, setAnchorElement] = useState<HTMLElement | null>(null);
  const menuOpen = Boolean(anchorElement);
  const triggerIcon = resolvedMode === "dark" ? <DarkModeOutlinedIcon /> : <LightModeOutlinedIcon />;

  const chooseMode = (nextMode: ThemePreference) => {
    setMode(nextMode);
    setAnchorElement(null);
  };

  return (
    <>
      <Tooltip title="Change color theme">
        <IconButton
          aria-controls={menuOpen ? "color-theme-menu" : undefined}
          aria-expanded={menuOpen ? "true" : undefined}
          aria-haspopup="menu"
          aria-label={`Change color theme. Current setting: ${mode}.`}
          color="inherit"
          onClick={(event: MouseEvent<HTMLElement>) => setAnchorElement(event.currentTarget)}
          size="small"
        >
          {triggerIcon}
        </IconButton>
      </Tooltip>
      <Menu
        anchorEl={anchorElement}
        anchorOrigin={{ horizontal: "right", vertical: "bottom" }}
        id="color-theme-menu"
        onClose={() => setAnchorElement(null)}
        open={menuOpen}
        slotProps={{ list: { "aria-label": "Color theme options" } }}
        transformOrigin={{ horizontal: "right", vertical: "top" }}
      >
        {themeChoices.map((choice) => (
          <MenuItem key={choice.value} onClick={() => chooseMode(choice.value)} selected={mode === choice.value}>
            <ListItemIcon>{choiceIcon(choice.value)}</ListItemIcon>
            <ListItemText>{choice.label}</ListItemText>
          </MenuItem>
        ))}
      </Menu>
    </>
  );
}
