"""Tests for Zen mode animated visualizer."""

from unittest.mock import patch

from radioactive.ui import handle_zen_mode, set_global_station_info


def test_handle_zen_mode_non_interactive(capsys):
    set_global_station_info(
        {
            "name": "Test Station",
            "tags": "rock,classic",
            "codec": "mp3",
            "bitrate": "128",
        }
    )

    with patch("sys.stdin.isatty", return_value=False), \
         patch("sys.stdout.isatty", return_value=False):
        handle_zen_mode()


def test_handle_zen_mode_interactive_exit(capsys):
    set_global_station_info({"name": "Chill Beats"})

    with patch("sys.stdin.isatty", return_value=True), \
         patch("sys.stdout.isatty", return_value=True), \
         patch("select.select", return_value=([True], [], [])), \
         patch("sys.stdin.read", return_value="q"), \
         patch("termios.tcgetattr", return_value=[]), \
         patch("tty.setcbreak"), \
         patch("termios.tcsetattr"):
        handle_zen_mode()
