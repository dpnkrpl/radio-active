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


def test_handle_zen_mode_with_volume_and_metadata(capsys):
    set_global_station_info(
        {
            "name": "Jazz FM",
            "tags": "jazz,smooth",
            "codec": "AAC",
            "bitrate": "320",
            "country": "United Kingdom",
            "volume": 75,
        }
    )

    with patch("sys.stdin.isatty", return_value=False), \
         patch("sys.stdout.isatty", return_value=False):
        handle_zen_mode(volume=90)


def test_handle_zen_mode_all_styles(capsys):
    set_global_station_info(
        {
            "name": "Synthwave Arcade",
            "tags": "retrowave,synth",
            "codec": "FLAC",
            "bitrate": "1411",
            "country": "France",
            "volume": 85,
        }
    )

    with patch("sys.stdin.isatty", return_value=False), \
         patch("sys.stdout.isatty", return_value=False):
        for style_idx in range(4):
            handle_zen_mode(volume=85, style=style_idx)


def test_handle_zen_mode_space_cycle_and_exit():
    set_global_station_info({"name": "Chill Beats"})

    # Simulate pressing ' ' twice (switching styles) then 'q' (exit)
    read_mock_sequence = [" ", " ", "q"]

    with patch("sys.stdin.isatty", return_value=True), \
         patch("sys.stdout.isatty", return_value=True), \
         patch("select.select", return_value=([True], [], [])), \
         patch("sys.stdin.read", side_effect=read_mock_sequence), \
         patch("termios.tcgetattr", return_value=[]), \
         patch("tty.setcbreak"), \
         patch("termios.tcsetattr"):
        handle_zen_mode(style=0)


def test_handle_zen_mode_with_track_marquee(capsys):
    set_global_station_info(
        {
            "name": "Lofi Girl",
            "tags": "lofi,hiphop",
            "track": "Kavv - Midnight Bloom",
            "url_resolved": "http://stream.example.com/radio.mp3",
            "volume": 70,
        }
    )

    with patch("sys.stdin.isatty", return_value=False), \
         patch("sys.stdout.isatty", return_value=False):
        handle_zen_mode(track="Kavv - Midnight Bloom")


def test_handle_vim_style_prompt_inactivity_timeout():
    from radioactive.utilities import handle_vim_style_prompt

    # Mock get_key returning None (simulating timeout on input)
    with patch("radioactive.utilities.get_key", return_value=None):
        # Setting inactivity_timeout to a tiny duration so it triggers immediately
        res = handle_vim_style_prompt(alias=None, history=None, inactivity_timeout=0.01)
        assert res == "z"
