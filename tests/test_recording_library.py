"""Tests for recording library and file shazam actions."""

import os
from unittest.mock import MagicMock, patch
import pytest

from radioactive.actions import (
    handle_play_recording,
    handle_recording_library,
    handle_shazam_file,
)


def test_handle_shazam_file_nonexistent(caplog):
    handle_shazam_file("/path/to/nonexistent/file.mp3")


def test_handle_shazam_file_success(tmp_path):
    test_file = tmp_path / "test_track.mp3"
    test_file.write_bytes(b"dummy audio content")

    mock_track_data = {
        "track": {
            "title": "Bohemian Rhapsody",
            "subtitle": "Queen",
        }
    }

    with patch("radioactive.actions._identify_music", return_value=mock_track_data), \
         patch("radioactive.actions.handle_notification") as mock_notify, \
         patch("radioactive.ui.handle_shazam_popup") as mock_popup:
        handle_shazam_file(str(test_file))
        mock_notify.assert_called_once_with("Song Identified", "Bohemian Rhapsody - Queen")
        mock_popup.assert_called_once_with(mock_track_data)


def test_handle_play_recording(tmp_path):
    test_file = tmp_path / "play_test.mp3"
    test_file.write_bytes(b"dummy audio")

    with patch("shutil.which", return_value="/usr/bin/ffplay"), \
         patch("subprocess.run") as mock_run:
        handle_play_recording(str(test_file))
        mock_run.assert_called_once_with(
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "warning", str(test_file)]
        )


def test_recording_library_empty(tmp_path):
    with patch("radioactive.paths.get_recordings_path", return_value=str(tmp_path)):
        handle_recording_library()


def test_recording_library_cancel_first(tmp_path):
    rec_dir = tmp_path / "recordings"
    rec_dir.mkdir()
    (rec_dir / "station1.mp3").write_bytes(b"audio1")

    # Pick index 0 (Cancel / Back) immediately
    with patch("radioactive.paths.get_recordings_path", return_value=str(rec_dir)), \
         patch("pick.pick", return_value=("🔙 [ Cancel / Back ]", 0)):
        handle_recording_library()


def test_recording_library_play(tmp_path):
    rec_dir = tmp_path / "recordings"
    rec_dir.mkdir()
    file1 = rec_dir / "station1.mp3"
    file1.write_bytes(b"audio1")

    pick_side_effects = [
        ("🎵 station1.mp3", 1),
        ("▶️  Play recording", 0),
    ]

    with patch("radioactive.paths.get_recordings_path", return_value=str(rec_dir)), \
         patch("pick.pick", side_effect=pick_side_effects):
        rec_name, rec_url = handle_recording_library()
        assert rec_name == "station1.mp3"
        assert rec_url == str(file1)


def test_recording_library_rename(tmp_path):
    rec_dir = tmp_path / "recordings"
    rec_dir.mkdir()
    file1 = rec_dir / "station1.mp3"
    file1.write_bytes(b"audio1")

    # Flow:
    # 1. Pick file 1 ("station1.mp3")
    # 2. Pick action 2 (Rename)
    # 3. Enter new name "renamed_station"
    # 4. In next loop iteration, pick index 0 (Cancel / Back)
    pick_side_effects = [
        ("🎵 station1.mp3", 1),
        ("✏️  Rename", 2),
        ("🔙 [ Cancel / Back ]", 0),
    ]

    with patch("radioactive.paths.get_recordings_path", return_value=str(rec_dir)), \
         patch("pick.pick", side_effect=pick_side_effects), \
         patch("builtins.input", return_value="renamed_station"):
        handle_recording_library()

    assert not (rec_dir / "station1.mp3").exists()
    assert (rec_dir / "renamed_station.mp3").exists()


def test_recording_library_delete(tmp_path):
    rec_dir = tmp_path / "recordings"
    rec_dir.mkdir()
    file1 = rec_dir / "station_to_del.mp3"
    file1.write_bytes(b"audio_to_del")

    # Flow:
    # 1. Pick file 1 ("station_to_del.mp3")
    # 2. Pick action 3 (Delete)
    # 3. Input confirmation "y"
    # 4. Library becomes empty and exits automatically
    pick_side_effects = [
        ("🎵 station_to_del.mp3", 1),
        ("🗑️  Delete", 3),
    ]

    with patch("radioactive.paths.get_recordings_path", return_value=str(rec_dir)), \
         patch("pick.pick", side_effect=pick_side_effects), \
         patch("builtins.input", return_value="y"):
        handle_recording_library()

    assert not (rec_dir / "station_to_del.mp3").exists()


def test_recording_library_shazam(tmp_path):
    rec_dir = tmp_path / "recordings"
    rec_dir.mkdir()
    file1 = rec_dir / "song.mp3"
    file1.write_bytes(b"song_audio")

    pick_side_effects = [
        ("🎵 song.mp3", 1),
        ("🔍 Shazam (Identify song)", 1),
        ("🔙 [ Cancel / Back ]", 0),
    ]

    with patch("radioactive.paths.get_recordings_path", return_value=str(rec_dir)), \
         patch("pick.pick", side_effect=pick_side_effects), \
         patch("radioactive.actions.handle_shazam_file") as mock_shazam:
        handle_recording_library()
        mock_shazam.assert_called_once_with(str(file1))
