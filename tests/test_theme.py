from unittest.mock import patch
import pytest

from radioactive.theme import (
    THEMES,
    THEME_ALIASES,
    get_available_themes,
    get_current_theme,
    get_theme,
    set_current_theme,
)
from radioactive.config import Configs
from radioactive.args import Parser
from radioactive.ui import (
    handle_welcome_screen,
    handle_favorite_table,
    handle_history_table,
    handle_current_play_panel,
    handle_zen_mode,
    set_global_station_info,
)


def test_available_themes():
    themes = get_available_themes()
    expected = ["default", "cyberpunk", "matrix", "amber", "nordic"]
    for name in expected:
        assert name in themes
        assert name in THEMES


def test_get_theme_names_and_aliases():
    assert get_theme("cyberpunk").name == "cyberpunk"
    assert get_theme("neon").name == "cyberpunk"
    assert get_theme("synthwave").name == "cyberpunk"

    assert get_theme("matrix").name == "matrix"
    assert get_theme("hacker").name == "matrix"
    assert get_theme("green").name == "matrix"

    assert get_theme("amber").name == "amber"
    assert get_theme("retro").name == "amber"
    assert get_theme("hifi").name == "amber"

    assert get_theme("nordic").name == "nordic"
    assert get_theme("nord").name == "nordic"
    assert get_theme("pastel").name == "nordic"

    assert get_theme("classic").name == "default"
    assert get_theme(None).name == "default"
    assert get_theme("nonexistent_theme").name == "default"


def test_set_current_theme():
    set_current_theme("cyberpunk")
    assert get_current_theme().name == "cyberpunk"

    set_current_theme("matrix")
    assert get_current_theme().name == "matrix"

    set_current_theme("amber")
    assert get_current_theme().name == "amber"

    set_current_theme("nordic")
    assert get_current_theme().name == "nordic"

    set_current_theme("default")
    assert get_current_theme().name == "default"


def test_config_loads_theme(tmp_path):
    config_file = tmp_path / "config.ini"
    config_file.write_text("[AppConfig]\ntheme = cyberpunk\n")

    with patch("radioactive.paths.get_config_path", return_value=str(config_file)):
        configs = Configs()
        opts = configs.load()
        assert opts.get("theme") == "cyberpunk"


def test_cli_theme_argument():
    with patch("sys.argv", ["radioactive", "--theme", "matrix"]):
        p = Parser()
        res = p.parse()
        assert res.theme == "matrix"


from radioactive.actions import handle_theme_selection


def test_ui_components_with_all_themes(capsys):
    set_global_station_info({"name": "Test Station", "codec": "MP3", "bitrate": "128"})

    for theme_name in ["default", "cyberpunk", "matrix", "amber", "nordic"]:
        set_current_theme(theme_name)
        handle_welcome_screen()
        handle_current_play_panel("Test Station")
        handle_zen_mode()

    # Reset back to default
    set_current_theme("default")


def test_handle_theme_selection_cancel():
    # User selects index 0 (Cancel / Back)
    with patch("pick.pick", return_value=("🔙 [ Cancel / Back ]", 0)):
        result = handle_theme_selection()
        assert result is None


def test_handle_theme_selection_apply():
    # User selects index 2 (Cyberpunk)
    with patch("pick.pick", return_value=("⚡ Cyberpunk", 2)):
        result = handle_theme_selection()
        assert result == "cyberpunk"
        assert get_current_theme().name == "cyberpunk"

    # User selects index 3 (Matrix)
    with patch("pick.pick", return_value=("📟 Matrix", 3)):
        result = handle_theme_selection()
        assert result == "matrix"
        assert get_current_theme().name == "matrix"

    # Reset
    set_current_theme("default")


def test_handle_theme_selection_exception():
    with patch("pick.pick", side_effect=KeyboardInterrupt):
        result = handle_theme_selection()
        assert result is None
