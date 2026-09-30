"""Tests for Ffplay error handling and playback robustness."""

from unittest.mock import MagicMock, patch
import io
import pytest

from radioactive.ffplay import Ffplay


def test_ffplay_ignores_ansi_and_dropped_escape():
    with patch("shutil.which", return_value="/usr/bin/ffplay"), \
         patch("subprocess.Popen") as mock_popen:
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None  # Process is running
        mock_popen.return_value = mock_proc

        player = Ffplay("http://fake.stream", 80, "info")

        # Simulate stderr output with ANSI escapes and Dropped Escape call
        mock_proc.stderr.readline.side_effect = [
            "\x1b[2K\r\x1b[2K\r",
            "Dropped Escape call with ulEscapeCode : 0x03007703\n",
            ValueError("closed"),
        ]

        # Running the error output check should NOT stop playback because process is alive and lines are benign
        player._check_error_output()

        assert player.is_playing is True
        assert mock_proc.terminate.call_count == 0


def test_ffplay_handles_fatal_error_when_process_exits():
    with patch("shutil.which", return_value="/usr/bin/ffplay"), \
         patch("subprocess.Popen") as mock_popen:
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 1  # Process exited with error
        mock_popen.return_value = mock_proc

        player = Ffplay("http://fake.stream", 80, "info")

        mock_proc.stderr.readline.side_effect = [
            "Server returned 404 Not Found\n",
        ]

        player._check_error_output()

        assert player.is_playing is False
