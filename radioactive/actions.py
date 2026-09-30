"""
Core logical actions for radio-active.
"""

import asyncio
import datetime
import json
import os
import subprocess
import sys
from random import randint
from typing import Any, Dict, List, Optional, Tuple, Union

import requests
from zenlog import log

try:
    from radioactive.feature_flags import RECORDING_FEATURE
except ImportError:
    # Default to True if file not found (e.g. dev mode without configure)
    RECORDING_FEATURE = True

if RECORDING_FEATURE:
    from radioactive.recorder import record_audio_auto_codec, record_audio_from_url

from radioactive.last_station import Last_station


def handle_notification(title: str, message: str, icon: str = None) -> None:
    """Send a desktop notification on Linux."""
    from shutil import which

    from radioactive.paths import get_logo_path

    if which("notify-send"):
        if not icon:
            icon = get_logo_path()

        cmd = ["notify-send", "-a", "radioactive", "-u", "normal"]
        if icon:
            cmd.extend(["-i", icon])

        cmd.extend([title, message])

        try:
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            log.debug(f"Error sending notification: {e}")
    else:
        log.error(
            "notify-send is not installed. please install it to use notifications"
        )


def get_current_track_name(url: str) -> str:
    """Fetch currently playing track information and return it"""
    # Run ffprobe command and capture the metadata
    # -i is implicit if it's the last arg, but let's be explicit
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-select_streams",
        "a:0",
        "-show_entries",
        "format_tags=StreamTitle",
        "-print_format",
        "json",
        url,
    ]
    track_name = ""

    try:
        # 10 second timeout for the ffprobe command itself
        output = subprocess.check_output(cmd, timeout=10).decode("utf-8")
        data = json.loads(output)
        log.debug(f"station info: {data}")

        # Extract the song title (StreamTitle) if available
        # It's usually in format -> tags -> StreamTitle
        track_name = (
            data.get("format", {}).get("tags", {}).get("StreamTitle", "").strip()
        )
    except subprocess.TimeoutExpired:
        log.debug("Track info fetch timed out")
    except Exception as e:
        log.debug(f"Error while fetching the track name: {e}")

    return track_name


def handle_fetch_song_title(url: str) -> None:
    """Fetch currently playing track information"""
    log.info("Fetching the current track info")
    log.debug(f"Attempting to retrieve track info from: {url}")

    track_name = get_current_track_name(url)

    if track_name != "":
        log.info(f"🎶: {track_name}")
        try:
            from radioactive.ui import get_global_station_info, set_global_station_info

            info = get_global_station_info()
            info["track"] = track_name
            info["title"] = track_name
            set_global_station_info(info)
        except Exception:
            pass
    else:
        log.error("No track information available")


def handle_record(
    target_url: str,
    curr_station_name: str,
    record_file_path: str,
    record_file: str,
    record_file_format: str,  # auto/mp3
    loglevel: str,
    duration: Optional[int] = None,
) -> None:
    """
    Handle audio recording logic.
    """
    if not RECORDING_FEATURE:
        log.error("Recording feature is not compiled/enabled in this build.")
        return

    # log.info("Press 'q' to stop recording")
    force_mp3 = False

    if record_file_format != "mp3" and record_file_format != "auto":
        record_file_format = "mp3"  # default to mp3
        log.debug("Error: wrong codec supplied!. falling back to mp3")
        force_mp3 = True
    elif record_file_format == "auto":
        log.debug("Codec: fetching stream codec")
        codec = record_audio_auto_codec(target_url)
        if codec is None:
            record_file_format = "mp3"  # default to mp3
            force_mp3 = True
            log.debug("Error: could not detect codec. falling back to mp3")
        else:
            record_file_format = codec
            log.debug(f"Codec: found {codec}")
    elif record_file_format == "mp3":
        # always save to mp3 to eliminate any runtime issues
        # it is better to leave it on libmp3lame
        force_mp3 = True

    if record_file_path and not os.path.exists(record_file_path):
        log.debug(f"filepath: {record_file_path}")
        try:
            os.makedirs(record_file_path, exist_ok=True)
        except Exception as e:
            log.error(f"Could not create recording directory: {e}")

    elif not record_file_path:
        from radioactive.paths import get_recordings_path

        log.debug("filepath: fallback to default path")
        record_file_path = get_recordings_path()
        try:
            os.makedirs(record_file_path, exist_ok=True)
        except Exception as e:
            log.error(f"Could not create recording directory: {e}")
            log.warning("Recording might fail if the directory is not writable.")
            # We don't exit here, we try to proceed or return?
            # If we return, recording stops but app stays alive.
            # But earlier code sys.exit(1).
            # User wants NO CRASH.
            # Let's try to verify if we can write there?
            # For now, just catching the exception is enough to stop the crash.

    now = datetime.datetime.now()
    month_name = now.strftime("%b").upper()
    # Format AM/PM as 'AM' or 'PM'
    am_pm = now.strftime("%p")

    # format is : day-monthname-year@hour-minute-second-(AM/PM)
    formatted_date_time = now.strftime(f"%d-{month_name}-%Y@%I-%M-%S-{am_pm}")

    if not record_file_format.strip():
        record_file_format = "mp3"

    if not record_file:
        record_file = "{}-{}".format(
            curr_station_name.strip(), formatted_date_time
        ).replace(" ", "-")

    tmp_filename = f"{record_file}.{record_file_format}"
    outfile_path = os.path.join(record_file_path, tmp_filename)

    process = record_audio_from_url(
        target_url,
        outfile_path,
        force_mp3,
        loglevel,
        duration,
        station_name=curr_station_name,
    )
    return process, outfile_path


def handle_add_station(alias) -> None:
    """Add a new station to favorites via user input."""
    try:
        left = input("Enter station name:")
        right = input("Enter station stream-url or radio-browser uuid:")
    except EOFError:
        print()
        log.debug("Ctrl+D (EOF) detected. Exiting gracefully.")
        sys.exit(0)

    if left.strip() == "" or right.strip() == "":
        log.error("Empty inputs not allowed")
        return
    alias.add_entry(left, right)
    log.info("New entry: {}={} added\n".format(left, right))


def handle_add_to_favorite(alias, station_name: str, station_uuid_url: str) -> None:
    """Add the current station to favorites."""
    try:
        response = alias.add_entry(station_name, station_uuid_url)
        if not response:
            try:
                user_input = input("Enter a different name: ")
            except EOFError:
                print()
                log.debug("Ctrl+D (EOF) detected. Exiting gracefully.")
                sys.exit(0)

            if user_input.strip() != "":
                response = alias.add_entry(user_input.strip(), station_uuid_url)
    except Exception as e:
        log.debug(f"Error: {e}")
        log.error("Could not add to favorite. Already in list?")


def handle_save_last_station(last_station, station_name: str, station_url: str) -> None:
    """Save the last played station."""
    # last_station = Last_station() # Provided as arg now

    last_played_station = {}
    last_played_station["name"] = station_name.strip()
    last_played_station["uuid_or_url"] = station_url.strip()

    log.debug(f"Saving the current station: {last_played_station}")
    last_station.save_info(last_played_station)


def handle_save_to_history(history, station_name: str, station_url: str) -> None:
    """Save the current station to history."""
    try:
        from radioactive.feature_flags import HISTORY_FEATURE

        if not HISTORY_FEATURE:
            return
    except ImportError:
        pass

    station_data = {}
    station_data["name"] = station_name
    station_data["uuid_or_url"] = station_url

    # try to get richer info
    from radioactive.ui import get_global_station_info

    global_info = get_global_station_info()
    if global_info and global_info.get("name") == station_name:
        # use global info but ensure required keys
        station_data.update(global_info)

    # re-ensure required keys
    station_data["name"] = station_name.strip()
    station_data["uuid_or_url"] = station_url.strip()

    log.debug(f"Adding to history: {station_name}")
    history.append(station_data)


def check_sort_by_parameter(sort_by: str) -> str:
    """Validate and return the sort parameter."""
    accepted_parameters = [
        "name",
        "votes",
        "codec",
        "bitrate",
        "lastcheckok",
        "lastchecktime",
        "clickcount",
        "clicktrend",
        "random",
    ]

    if sort_by not in accepted_parameters:
        log.warning("Sort parameter is unknown. Falling back to 'name'")

        log.warning(
            "choose from: name,votes,codec,bitrate,lastcheckok,lastchecktime,clickcount,clicktrend,random"
        )
        return "name"
    return sort_by


def handle_search_stations(
    handler, station_name: str, limit: int, sort_by: str, filter_with: str
) -> Any:
    """Wrapper to search stations by name."""
    log.debug(f"Searching API for: {station_name}")
    return handler.search_by_station_name(station_name, limit, sort_by, filter_with)


def handle_station_uuid_play(handler, station_uuid: str) -> Tuple[str, str]:
    """Play a station by UUID and register a vote."""
    log.debug(f"Searching API for: {station_uuid}")

    handler.play_by_station_uuid(station_uuid)

    log.debug(f"increased click count for: {station_uuid}")

    handler.vote_for_uuid(station_uuid)
    try:
        station_name = handler.target_station["name"]
        station_url = handler.target_station["url"]
    except Exception as e:
        log.debug(f"{e}")
        log.error("Something went wrong")
        return None, None

    return station_name, station_url


def handle_direct_play(
    alias, history=None, station_name_or_url: str = ""
) -> Tuple[str, str]:
    """Play a station directly with UUID or direct stream URL."""
    if "://" in station_name_or_url.strip():
        log.debug("Direct play: URL provided")
        # stream URL
        # call using URL with no station name N/A
        # attempt to get station name from metadata
        station_name = handle_get_station_name_from_metadata(station_name_or_url)
        return station_name, station_name_or_url
    else:
        log.debug("Direct play: station name provided")
        # search in favorites first
        response = alias.search(station_name_or_url)

        # if not found, check history
        if not response and history:
            log.debug("Not found in favorites, checking history")
            if hasattr(history, "search"):
                response = history.search(station_name_or_url)

        if not response:
            log.debug(f"Search failed for: {station_name_or_url}")
            log.error(
                "No station found on your favorite list or history with that name"
            )
            return None, None
        else:
            log.debug(f"Direct play found: {response}")
            return response["name"], response.get("uuid_or_url") or response.get(
                "stationuuid"
            )


def handle_play_last_station(last_station) -> Tuple[str, str]:
    """Play the last played station."""
    station_obj = last_station.get_info()
    return station_obj["name"], station_obj["uuid_or_url"]


def handle_get_station_name_from_metadata(url: str) -> str:
    """Get ICY metadata from ffprobe to find station name."""
    log.info("Fetching the station name")
    log.debug(f"Attempting to retrieve station name from: {url}")
    # Run ffprobe command and capture the metadata
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_entries",
        "format=icy",
        url,
    ]
    station_name = "Unknown Station"

    try:
        output = subprocess.check_output(cmd).decode("utf-8")
        data = json.loads(output)
        log.debug(f"station info: {data}")

        # Extract the station name (icy-name) if available
        station_name = (
            data.get("format", {}).get("tags", {}).get("icy-name", "Unknown Station")
        )
    except Exception:
        log.error("Could not fetch the station name")

    return station_name


def handle_station_name_from_headers(url: str) -> str:
    """
    Get headers from URL to find station name (deprecated).
    """
    log.info("Fetching the station name")
    log.debug(f"Attempting to retrieve station name from: {url}")
    station_name = "Unknown Station"
    try:
        # sync call, with timeout
        response = requests.get(url, timeout=5)
        if response.status_code == requests.codes.ok:
            if response.headers.get("Icy-Name"):
                station_name = response.headers.get("Icy-Name")
            else:
                log.error("Station name not found")
        else:
            log.debug(f"Response code received is: {response.status_code}")
    except Exception as e:
        log.error("Could not fetch the station name")
        log.debug(f"An error occurred: {e}")
    return station_name


def handle_play_random_station(alias) -> Tuple[str, str]:
    """Select a random station from favorite menu."""
    log.debug("playing a random station")
    alias_map = alias.alias_map
    if not alias_map:
        log.error("No favorite stations found")
        return None, None

    index = randint(0, len(alias_map) - 1)
    station = alias_map[index]
    return station["name"], station["uuid_or_url"]


async def _identify_music(audio_path):
    """Internal async helper for Shazam identification."""
    try:
        from shazamio import Shazam

        shazam = Shazam()
        out = await shazam.recognize(audio_path)
        return out
    except Exception as e:
        log.debug(f"Shazam identification failed: {e}")
        return None


def handle_shazam(target_url: str):
    """
    Record 7 seconds of audio and identify using Shazam.
    """
    import tempfile

    if not target_url:
        log.error("No station is playing, cannot identify.")
        return

    log.info("Identifying current song (7 seconds) ...")

    # Create temp file
    temp_dir = tempfile.gettempdir()
    temp_file = os.path.join(temp_dir, "radioactive_shazam.mp3")
    log.debug(f"temp_file: {temp_file}")

    # ffmpeg command to record 7 seconds
    # we use libmp3lame to ensure it's a valid mp3 for shazam
    cmd = [
        "ffmpeg",
        "-y",  # overwrite
        "-i",
        target_url,
        "-t",
        "7",
        "-c:a",
        "libmp3lame",
        "-loglevel",
        "error",
        temp_file,
    ]

    try:
        # Run ffmpeg synchronously (blocking for 7s)
        subprocess.run(cmd, check=True)

        if os.path.exists(temp_file) and os.path.getsize(temp_file) > 0:
            # shazamio is async, we need a runner
            result = asyncio.run(_identify_music(temp_file))

            if result and result.get("track"):
                track = result.get("track")
                title = track.get("title")
                artist = track.get("subtitle")
                log.info(f"🎶 Match found: {title} -- {artist}")

                # Also send a notification if possible
                handle_notification("Song Identified", f"{title} - {artist}")

                # Show the popup with all details
                from radioactive.ui import handle_shazam_popup

                handle_shazam_popup(result)
            else:
                log.warning("No match found for this song.")
        else:
            log.error("Could not record audio for identification.")

    except subprocess.CalledProcessError:
        log.error("FFmpeg error while recording for identification.")
    except Exception as e:
        log.error(f"Error during identification: {e}")
    finally:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass


def handle_shazam_file(audio_path: str) -> None:
    """
    Identify an audio file using Shazam.
    """
    if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
        log.error(f"Recording file '{audio_path}' not found or is empty.")
        return

    log.info(f"Identifying song from '{os.path.basename(audio_path)}' using Shazam ...")
    try:
        result = asyncio.run(_identify_music(audio_path))

        if result and result.get("track"):
            track = result.get("track")
            title = track.get("title")
            artist = track.get("subtitle")
            log.info(f"🎶 Match found: {title} -- {artist}")

            # Send notification if possible
            handle_notification("Song Identified", f"{title} - {artist}")

            # Show the popup with all details
            from radioactive.ui import handle_shazam_popup

            handle_shazam_popup(result)
        else:
            log.warning("No match found for this recording.")
    except Exception as e:
        log.error(f"Error during identification: {e}")


def handle_play_recording(audio_path: str) -> None:
    """
    Play a recorded audio file using ffplay, mpv, or vlc.
    """
    if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
        log.error(f"Recording file '{audio_path}' not found or is empty.")
        return

    from shutil import which

    filename = os.path.basename(audio_path)
    log.info(f"▶️ Playing recording: {filename}")
    log.info("Playback started. Press 'q' or Ctrl+C to stop / return.")

    cmd = None
    if which("ffplay"):
        cmd = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "warning", audio_path]
    elif which("mpv"):
        cmd = ["mpv", "--no-video", audio_path]
    elif which("cvlc"):
        cmd = ["cvlc", "--play-and-exit", audio_path]
    elif which("vlc"):
        cmd = ["vlc", "-I", "dummy", "--play-and-exit", audio_path]
    else:
        log.error("No audio player found (ffplay, mpv, or vlc required).")
        return

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        log.error(f"Error playing recording: {e}")


def handle_recording_library() -> Tuple[Optional[str], Optional[str]]:
    """
    Interactive recording library manager.
    Allows user to select a recording, play, rename, delete, or Shazam it.
    Returns (recording_name, recording_filepath) if user chose to play, otherwise (None, None).
    """
    from pick import pick

    from radioactive.paths import get_recordings_path

    recordings_path = get_recordings_path()
    if not os.path.exists(recordings_path):
        log.info(f"Recordings directory does not exist: {recordings_path}")
        return None, None

    while True:
        try:
            entries = [
                f
                for f in os.listdir(recordings_path)
                if os.path.isfile(os.path.join(recordings_path, f))
                and not f.startswith(".")
            ]
        except Exception as e:
            log.error(f"Could not read recordings directory: {e}")
            return None, None

        if not entries:
            log.info("No recordings found in your library.")
            return None, None

        # Sort by modification time (newest first)
        entries.sort(
            key=lambda f: os.path.getmtime(os.path.join(recordings_path, f)),
            reverse=True,
        )

        title = "📼 Recording Library - Select a recording:\n(Use Up/Down arrows and Enter to select)"
        options = ["🔙 [ Cancel / Back ]"] + [f"🎵 {f}" for f in entries]

        try:
            _, index = pick(options, title, indicator="-->")
        except Exception as e:
            log.debug(f"Menu error or cancelled: {e}")
            return None, None

        if index == 0:
            # First entry is Cancel / Back
            return None, None

        selected_filename = entries[index - 1]
        selected_filepath = os.path.join(recordings_path, selected_filename)

        action_title = f"📼 Selected: {selected_filename}\nChoose an action:"
        action_options = [
            "▶️  Play recording",
            "🔍 Shazam (Identify song)",
            "✏️  Rename",
            "🗑️  Delete",
            "🔙 Back to recordings list",
        ]

        try:
            _, action_idx = pick(action_options, action_title, indicator="-->")
        except Exception as e:
            log.debug(f"Action menu error or cancelled: {e}")
            continue

        if action_idx == 0:
            # Play recording via main player
            return selected_filename, selected_filepath

        elif action_idx == 1:
            # Shazam identify
            handle_shazam_file(selected_filepath)

        elif action_idx == 2:
            # Rename
            try:
                print(f"\nCurrent filename: {selected_filename}")
                new_name = input("Enter new filename (leave blank to cancel): ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                continue

            if not new_name:
                log.info("Rename cancelled.")
                continue

            # Strip any directory traversal characters
            new_name = os.path.basename(new_name)

            # Preserve extension if not specified in new name
            _, orig_ext = os.path.splitext(selected_filename)
            if "." not in new_name and orig_ext:
                new_name = f"{new_name}{orig_ext}"

            new_filepath = os.path.join(recordings_path, new_name)
            if os.path.exists(new_filepath) and new_filepath != selected_filepath:
                log.error(f"A file named '{new_name}' already exists.")
                continue

            try:
                os.rename(selected_filepath, new_filepath)
                log.info(f"Renamed '{selected_filename}' -> '{new_name}' successfully!")
            except Exception as e:
                log.error(f"Failed to rename file: {e}")

        elif action_idx == 3:
            # Delete
            try:
                confirm = (
                    input(
                        f"Are you sure you want to delete '{selected_filename}'? (y/N): "
                    )
                    .strip()
                    .lower()
                )
            except (EOFError, KeyboardInterrupt):
                print()
                continue

            if confirm in ["y", "yes"]:
                try:
                    os.remove(selected_filepath)
                    log.info(f"Deleted '{selected_filename}' successfully.")
                except Exception as e:
                    log.error(f"Failed to delete recording: {e}")
            else:
                log.info("Deletion cancelled.")

        elif action_idx == 4:
            # Back
            continue


def handle_theme_selection() -> Optional[str]:
    """
    Interactive UI theme selector.
    Allows user to switch the active theme at runtime.
    """
    from pick import pick

    from radioactive.theme import get_current_theme, set_current_theme

    current = get_current_theme().name

    theme_list = [
        ("default", "🎨 Default (Classic Magenta / Cyan)"),
        ("cyberpunk", "⚡ Cyberpunk / Neon (Electric Cyan / Hot Pink)"),
        ("matrix", "📟 Matrix (Phosphor Green / Black)"),
        ("amber", "📻 Amber / Retro Hi-Fi (Warm Amber / Gold)"),
        ("nordic", "❄️  Nordic / Pastel (Ice Blue / Slate Frost)"),
    ]

    title = "🎨 UI Theme Selector - Select a color theme:\n(Use Up/Down arrows and Enter to apply)"
    options = ["🔙 [ Cancel / Back ]"]
    for code, label in theme_list:
        if code == current:
            options.append(f"{label}  [active]")
        else:
            options.append(label)

    try:
        _, index = pick(options, title, indicator="-->")
    except (Exception, KeyboardInterrupt) as e:
        log.debug(f"Theme selection cancelled or error: {e}")
        return None

    if index == 0:
        return None

    selected_code = theme_list[index - 1][0]
    set_current_theme(selected_code)
    log.info(f"Theme switched to: {selected_code.capitalize()}")
    return selected_code
