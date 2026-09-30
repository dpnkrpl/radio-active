"""
Theme management for radio-active.
Provides customizable color palettes and styling tokens for CLI UI components.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Theme:
    name: str
    primary: str
    secondary: str
    accent: str
    text: str
    dim: str
    border: str
    header_style: str
    title_style: str
    visualizer_bars: List[str] = field(default_factory=list)
    visualizer_title_style: str = "bold bright_yellow"
    visualizer_meter_style: str = "dim cyan"
    success: str = "green"
    warning: str = "yellow"
    error: str = "bold red"


# Built-in themes
THEMES: Dict[str, Theme] = {
    "default": Theme(
        name="default",
        primary="magenta",
        secondary="cyan",
        accent="yellow",
        text="white",
        dim="dim white",
        border="white",
        header_style="bold magenta",
        title_style="bold white",
        visualizer_bars=[
            "#00f5d4",
            "#00b4d8",
            "#7209b7",
            "#ffbd00",
            "#ff5400",
            "#ff0054",
        ],
        visualizer_title_style="bold bright_yellow",
        visualizer_meter_style="dim cyan",
        success="green",
        warning="yellow",
        error="bold red",
    ),
    "cyberpunk": Theme(
        name="cyberpunk",
        primary="#ff007f",
        secondary="#00f0ff",
        accent="#b026ff",
        text="#e0f7fa",
        dim="#7c4dff",
        border="#00f0ff",
        header_style="bold #ff007f",
        title_style="bold #00f0ff",
        visualizer_bars=[
            "#00f0ff",
            "#39ff14",
            "#ffeb3b",
            "#ff007f",
            "#b026ff",
            "#ff0055",
        ],
        visualizer_title_style="bold #00f0ff",
        visualizer_meter_style="bold #b026ff",
        success="#39ff14",
        warning="#ffeb3b",
        error="#ff0055",
    ),
    "matrix": Theme(
        name="matrix",
        primary="#00ff66",
        secondary="#00cc44",
        accent="#33ff99",
        text="#a3ffb0",
        dim="#005522",
        border="#00cc44",
        header_style="bold #00ff66",
        title_style="bold #00ff66",
        visualizer_bars=[
            "#00441b",
            "#006d2c",
            "#238b45",
            "#41ab5d",
            "#74c476",
            "#a1d99b",
        ],
        visualizer_title_style="bold #00ff66",
        visualizer_meter_style="dim #00ff66",
        success="#00ff66",
        warning="#66ff99",
        error="#ff3333",
    ),
    "amber": Theme(
        name="amber",
        primary="#ffb000",
        secondary="#ff8c00",
        accent="#ffd700",
        text="#fff8e7",
        dim="#8c6239",
        border="#ffb000",
        header_style="bold #ffb000",
        title_style="bold #ffd700",
        visualizer_bars=[
            "#663300",
            "#994d00",
            "#cc6600",
            "#ff8000",
            "#ffb000",
            "#ffd700",
        ],
        visualizer_title_style="bold #ffd700",
        visualizer_meter_style="dim #ff8c00",
        success="#ffd700",
        warning="#ffb000",
        error="#ff3b00",
    ),
    "nordic": Theme(
        name="nordic",
        primary="#88c0d0",
        secondary="#81a1c1",
        accent="#ebcb8b",
        text="#eceff4",
        dim="#4c566a",
        border="#88c0d0",
        header_style="bold #88c0d0",
        title_style="bold #88c0d0",
        visualizer_bars=[
            "#5e81ac",
            "#81a1c1",
            "#88c0d0",
            "#8fbcbb",
            "#a3be8c",
            "#ebcb8b",
        ],
        visualizer_title_style="bold #ebcb8b",
        visualizer_meter_style="dim #81a1c1",
        success="#a3be8c",
        warning="#ebcb8b",
        error="#bf616a",
    ),
}

# Aliases mapping alternative names to standard theme names
THEME_ALIASES: Dict[str, str] = {
    "classic": "default",
    "neon": "cyberpunk",
    "synthwave": "cyberpunk",
    "hacker": "matrix",
    "green": "matrix",
    "retro": "amber",
    "hifi": "amber",
    "gold": "amber",
    "nord": "nordic",
    "pastel": "nordic",
    "frost": "nordic",
}

_current_theme: Theme = THEMES["default"]


def get_available_themes() -> List[str]:
    """Return a list of all primary available theme names."""
    return list(THEMES.keys())


def get_theme(name: Optional[str] = None) -> Theme:
    """
    Get a Theme instance by name or alias.
    If name is None or unknown, returns the default theme.
    """
    if not name:
        return THEMES["default"]

    clean_name = str(name).strip().lower()
    resolved_name = THEME_ALIASES.get(clean_name, clean_name)
    return THEMES.get(resolved_name, THEMES["default"])


def set_current_theme(name: str) -> Theme:
    """Set the globally active theme by name or alias."""
    global _current_theme
    _current_theme = get_theme(name)
    return _current_theme


def get_current_theme() -> Theme:
    """Get the currently active theme."""
    return _current_theme
