"""Tests for Settings runtime command, visualizer selection, and zen mode configuration."""

from unittest.mock import patch, MagicMock
import os
import pytest

from radioactive.config import Configs, save_config_option
from radioactive.actions import (
    handle_theme_selection,
    handle_visualizer_selection,
    handle_zen_mode_configuration,
    handle_settings,
)
from radioactive.ui import (
    get_default_zen_style,
    set_default_zen_style,
    get_zen_visualizer_styles,
    get_zen_show_volume,
    set_zen_show_volume,
    get_zen_show_track,
    set_zen_show_track,
    get_zen_show_visualizer,
    set_zen_show_visualizer,
    get_zen_timer,
    set_zen_timer,
    handle_zen_mode,
    set_global_station_info,
)
from radioactive.utilities import handle_vim_style_prompt


def test_save_and_load_config_settings(tmp_path):
    config_file = tmp_path / "config.ini"

    with patch("radioactive.paths.get_config_path", return_value=str(config_file)):
        save_config_option("theme", "matrix")
        save_config_option("visualizer", "2")
        save_config_option("zen_show_volume", "false")
        save_config_option("zen_show_track", "false")
        save_config_option("zen_show_visualizer", "false")
        save_config_option("zen_timer", "30")

        configs = Configs()
        opts = configs.load()
        assert opts.get("theme") == "matrix"
        assert opts.get("visualizer") == "2"
        assert opts.get("zen_show_volume") == "false"
        assert opts.get("zen_show_track") == "false"
        assert opts.get("zen_show_visualizer") == "false"
        assert opts.get("zen_timer") == "30"


def test_visualizer_getters_and_setters():
    styles = get_zen_visualizer_styles()
    assert len(styles) == 4
    assert "Spectrum Bars" in styles
    assert "Waveform Oscilloscope" in styles
    assert "Retro Tape Deck" in styles
    assert "Dot Matrix Peaks" in styles

    set_default_zen_style(1)
    assert get_default_zen_style() == 1

    set_default_zen_style("Retro Tape Deck")
    assert get_default_zen_style() == 2

    set_default_zen_style("3")
    assert get_default_zen_style() == 3

    # Reset
    set_default_zen_style(0)
    assert get_default_zen_style() == 0


def test_zenmode_getters_and_setters():
    set_zen_show_volume(False)
    assert get_zen_show_volume() is False
    set_zen_show_volume(True)
    assert get_zen_show_volume() is True

    set_zen_show_track(False)
    assert get_zen_show_track() is False
    set_zen_show_track(True)
    assert get_zen_show_track() is True

    set_zen_show_visualizer(False)
    assert get_zen_show_visualizer() is False
    set_zen_show_visualizer(True)
    assert get_zen_show_visualizer() is True

    set_zen_timer(45)
    assert get_zen_timer() == 45.0
    set_zen_timer("0")
    assert get_zen_timer() == 0.0
    set_zen_timer(15)
    assert get_zen_timer() == 15.0


def test_handle_visualizer_selection_cancel_and_apply():
    # Cancel
    with patch("pick.pick", return_value=("🔙 [ Cancel / Back ]", 0)):
        res = handle_visualizer_selection()
        assert res is None

    # Select Waveform Oscilloscope (index 2 in pick options, which maps to style 1)
    with patch("pick.pick", return_value=("2. Waveform Oscilloscope", 2)), \
         patch("radioactive.config.save_config_option"):
        res = handle_visualizer_selection()
        assert res == 1
        assert get_default_zen_style() == 1

    # Exception / cancel
    with patch("pick.pick", side_effect=KeyboardInterrupt):
        res = handle_visualizer_selection()
        assert res is None

    # Reset
    set_default_zen_style(0)


def test_handle_zen_mode_configuration_toggles():
    set_zen_show_volume(True)
    set_zen_show_track(True)
    set_zen_show_visualizer(True)
    set_zen_timer(15.0)

    # Simulate choosing:
    # 1 (Toggle Volume -> False)
    # 2 (Toggle Track -> False)
    # 3 (Toggle Visualizer -> False)
    # 0 (Back / Return)
    pick_sequence = [
        ("🔊 Show Volume", 1),
        ("🎵 Show Track Info", 2),
        ("📊 Show Visualizer", 3),
        ("🔙 [ Back to Settings ]", 0),
    ]

    with patch("pick.pick", side_effect=pick_sequence), \
         patch("radioactive.config.save_config_option"):
        handle_zen_mode_configuration()

    assert get_zen_show_volume() is False
    assert get_zen_show_track() is False
    assert get_zen_show_visualizer() is False

    # Reset
    set_zen_show_volume(True)
    set_zen_show_track(True)
    set_zen_show_visualizer(True)


def test_handle_zen_mode_configuration_timer_presets():
    # Simulate choosing 4 (Default Timer) -> preset 3 (60s) -> 0 (Back)
    main_menu_sequence = [
        ("⏱️  Default Zen Timer", 4),
        ("🔙 [ Back to Settings ]", 0),
    ]
    timer_menu_sequence = [
        ("⏱️  60 Seconds", 3),
    ]

    with patch("pick.pick", side_effect=[main_menu_sequence[0], timer_menu_sequence[0], main_menu_sequence[1]]), \
         patch("radioactive.config.save_config_option"):
        handle_zen_mode_configuration()

    assert get_zen_timer() == 60.0

    # Test custom timer input
    main_menu_seq2 = [
        ("⏱️  Default Zen Timer", 4),
        ("🔙 [ Back to Settings ]", 0),
    ]
    timer_menu_seq2 = [
        ("✏️  Custom Duration...", 7),
    ]
    with patch("pick.pick", side_effect=[main_menu_seq2[0], timer_menu_seq2[0], main_menu_seq2[1]]), \
         patch("builtins.input", return_value="42"), \
         patch("radioactive.config.save_config_option"):
        handle_zen_mode_configuration()

    assert get_zen_timer() == 42.0

    # Reset
    set_zen_timer(15.0)


def test_handle_settings_hub():
    # Sequence:
    # 1 (Theme) -> mocked
    # 2 (Visualizer) -> mocked
    # 3 (Zen mode) -> mocked
    # 0 (Back)
    pick_sequence = [
        ("🎨 1. Theme Selection", 1),
        ("📊 2. Default Visualizer", 2),
        ("🧘 3. Configure Zen Mode", 3),
        ("🔙 [ Back / Return ]", 0),
    ]

    with patch("pick.pick", side_effect=pick_sequence), \
         patch("radioactive.actions.handle_theme_selection") as mock_theme, \
         patch("radioactive.actions.handle_visualizer_selection") as mock_vis, \
         patch("radioactive.actions.handle_zen_mode_configuration") as mock_zen:
        handle_settings()
        assert mock_theme.called
        assert mock_vis.called
        assert mock_zen.called


def test_handle_zen_mode_with_disabled_elements(capsys):
    set_global_station_info(
        {
            "name": "Test Minimal Station",
            "tags": "ambient,electronic",
            "track": "Ambient Artist - Track 1",
            "volume": 70,
        }
    )

    # Test with volume disabled, track disabled, visualizer disabled
    set_zen_show_volume(False)
    set_zen_show_track(False)
    set_zen_show_visualizer(False)

    with patch("sys.stdin.isatty", return_value=False), \
         patch("sys.stdout.isatty", return_value=False):
        handle_zen_mode()

    # Reset
    set_zen_show_volume(True)
    set_zen_show_track(True)
    set_zen_show_visualizer(True)
