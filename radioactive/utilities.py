"""
Handler functions for __main__.py.
Acts as a controller/orchestrator, delegating to UI and Actions modules.
"""

import os
import sys
import threading
import time
from random import randint
from typing import Any, Dict, List, Optional, Tuple, Union

from pick import pick
from zenlog import log

try:
    from radioactive.feature_flags import (
        CYCLE_FEATURE,
        HISTORY_FEATURE,
        INFO_FEATURE,
        RECORDING_FEATURE,
        SEARCH_FEATURE,
        TIMER_FEATURE,
        TRACK_FEATURE,
    )
except ImportError:
    RECORDING_FEATURE = True
    TRACK_FEATURE = True
    SEARCH_FEATURE = True
    CYCLE_FEATURE = True
    INFO_FEATURE = True
    TIMER_FEATURE = True
    HISTORY_FEATURE = True

from radioactive.actions import (
    check_sort_by_parameter,
    get_current_track_name,
    handle_add_station,
    handle_add_to_favorite,
    handle_direct_play,
    handle_fetch_song_title,
    handle_get_station_name_from_metadata,
    handle_notification,
    handle_play_last_station,
    handle_play_random_station,
    handle_record,
    handle_recording_library,
    handle_save_last_station,
    handle_save_to_history,
    handle_search_stations,
    handle_settings,
    handle_shazam,
    handle_shazam_file,
    handle_station_name_from_headers,
    handle_station_uuid_play,
    handle_theme_selection,
    handle_visualizer_selection,
    handle_zen_mode_configuration,
)
from radioactive.ffplay import kill_background_ffplays

# Re-export functions for backward compatibility and aggregation
from radioactive.ui import (
    get_global_station_info,
    handle_current_play_panel,
    handle_favorite_table,
    handle_history_table,
    handle_recording_popup,
    handle_show_station_info,
    handle_update_modal,
    handle_update_screen,
    handle_welcome_screen,
    handle_zen_mode,
    set_global_station_info,
)

RED_COLOR = "\033[91m"
END_COLOR = "\033[0m"


def handle_station_selection_menu(handler, last_station, alias) -> Tuple[str, str]:
    """
    Show a selection menu for favorite stations.
    """
    # Add a selection list here. first entry must be the last played station
    # try to fetch the last played station's information
    last_station_info = {}
    try:
        last_station_info = last_station.get_info()
    except Exception as e:
        log.debug(f"Error: {e}")
        # no last station??
        pass

    title = "Please select a station from your favorite list:"
    station_selection_names = []
    station_selection_urls = []

    # add last played station first
    if last_station_info:
        station_selection_names.append(
            f"{last_station_info['name'].strip()} (last played station)"
        )
        uuid = last_station_info.get("stationuuid") or last_station_info.get(
            "uuid_or_url", ""
        )
        station_selection_urls.append(uuid)

    fav_stations = alias.alias_map
    for entry in fav_stations:
        station_selection_names.append(entry["name"].strip())
        station_selection_urls.append(entry["uuid_or_url"])

    options = station_selection_names
    if len(options) == 0:
        log.info(
            f"{RED_COLOR}No stations found in favorites or history. Entering idle mode.{END_COLOR}"
        )
        return None, None

    _, index = pick(options, title, indicator="-->")

    # check if there is direct URL or just UUID
    station_option_url = station_selection_urls[index]
    station_name = station_selection_names[index].replace("(last played station)", "")

    if station_option_url.find("://") != -1:
        # direct URL
        station_url = station_option_url
        return station_name, station_url

    else:
        # UUID
        station_uuid = station_option_url
        return handle_station_uuid_play(handler, station_uuid)


def get_key(timeout: Optional[float] = None) -> Optional[str]:
    """Helper to capture single key on Linux and Windows with optional timeout in seconds."""
    if not sys.stdin.isatty():
        try:
            line = sys.stdin.readline()
            return line.strip() if line else None
        except Exception:
            return None

    if sys.platform == "win32":
        import msvcrt
        import time

        if timeout is not None:
            start_t = time.time()
            while not msvcrt.kbhit():
                if time.time() - start_t >= timeout:
                    return None
                time.sleep(0.05)

        ch = msvcrt.getch()
        if ch in [b"\x00", b"\xe0"]:  # Special keys
            ch2 = msvcrt.getch()
            if ch2 == b"M":  # Right arrow
                return "\x1b[C"
            return ""

        if ch == b"\r":
            return "\n"
        if ch == b"\x08":
            return "\x08"

        try:
            return ch.decode("utf-8")
        except (UnicodeDecodeError, ValueError):
            return ""
    else:
        import select
        import termios
        import tty

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            if timeout is not None:
                r, _, _ = select.select([fd], [], [], timeout)
                if not r:
                    return None

            ch = sys.stdin.read(1)
            if ch == "\x1b":  # Escape sequence
                r, _, _ = select.select([fd], [], [], 0.05)
                if r:
                    seq = sys.stdin.read(2)
                    ch += seq
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def handle_vim_style_prompt(
    alias, history, inactivity_timeout: Optional[float] = None
) -> str:
    """Captured VIM style command prompt with fuzzy search and completions."""
    import time

    from rich.live import Live
    from rich.text import Text

    from radioactive.ui import get_zen_timer

    effective_timeout = (
        inactivity_timeout if inactivity_timeout is not None else get_zen_timer()
    )

    # Mapping of shortcut/command to descriptive full text
    command_map = {
        "p": "play/pause",
        "play": "play/pause",
        "t": "track info",
        "track": "track info",
        "i": "station info",
        "info": "station info",
        "r": "record",
        "record": "record",
        "rf": "record file",
        "rl": "recording library",
        "library": "recording library",
        "f": "add favorite",
        "fav": "add favorite",
        "list": "list favorites",
        "v+": "volume +",
        "v-": "volume -",
        "v": "set volume",
        "volume": "set volume",
        "s": "search",
        "search": "search",
        "n": "next station",
        "next": "next station",
        "a": "auto track info",
        "auto": "auto track info",
        "sz": "shazam identify",
        "shazam": "shazam identify",
        ".": "settings",
        "settings": "settings",
        "setting": "settings",
        "set": "settings",
        "theme": "theme selector",
        "themes": "theme selector",
        "timer": "timer",
        "sleep": "sleep",
        "b": "background",
        "background": "background",
        "q": "quit",
        "quit": "quit",
        "help": "help",
        "z": "zen mode",
        "zen": "zen mode",
        "?": "help",
    }

    # Combined list for matching
    completions = list(command_map.keys())

    # Build a list of station names for fuzzy search
    station_names = []
    if alias and hasattr(alias, "alias_map"):
        station_names += [s.get("name", "").strip() for s in alias.alias_map]
    if history and hasattr(history, "get_list"):
        station_names += [s.get("name", "").strip() for s in history.get_list()]

    # Clean and deduplicate station names
    station_names = sorted(list(set([n for n in station_names if n])))

    buffer = ""
    start_idle_time = time.time()

    def get_display(text, matches=None):
        if matches is None:
            matches = []
        # The prompt part
        prompt_text = Text("command : ", style="green")
        prompt_text.append(text, style="bold cyan")

        if buffer:
            # Check commands first
            cmd_matches = [m for m in completions if m.startswith(buffer)]
            if cmd_matches:
                first_match = cmd_matches[0]
                description = command_map.get(first_match, first_match)
                hint_text = Text(f"  ({description})", style="dim green")
                prompt_text.append(hint_text)
            else:
                # No command match, trigger fuzzy search for stations
                station_matches = [
                    n for n in station_names if buffer.lower() in n.lower()
                ]
                # simple sort by position of query in the name
                station_matches.sort(key=lambda n: n.lower().find(buffer.lower()))

                if station_matches:
                    first_match = station_matches[0]
                    hint_text = Text(f"  (~ {first_match})", style="italic dim yellow")
                    prompt_text.append(hint_text)

        return prompt_text

    with Live(get_display(""), transient=True, refresh_per_second=10) as live:
        while True:
            char = get_key(timeout=0.5)

            if char is None:
                # Idle slice - check if inactivity timeout reached
                if (
                    not buffer
                    and effective_timeout
                    and effective_timeout > 0
                    and (time.time() - start_idle_time >= effective_timeout)
                ):
                    return "z"
                continue

            # Key was pressed, reset idle timer
            start_idle_time = time.time()

            # Find current matches for logic below
            cmd_matches = [m for m in completions if buffer and m.startswith(buffer)]
            station_matches = []
            if not cmd_matches and buffer:
                station_matches = [
                    n for n in station_names if buffer.lower() in n.lower()
                ]
                station_matches.sort(key=lambda n: n.lower().find(buffer.lower()))

            if char in ["\r", "\n"]:  # Enter
                # If there's a fuzzy station match, use it. Otherwise use the buffer.
                if not cmd_matches and station_matches:
                    return station_matches[0]
                return buffer.strip()

            elif char in ["\x7f", "\x08"]:  # Backspace
                buffer = buffer[:-1]

            elif char == "\t" or char == "\x1b[C":  # Tab or Right Arrow
                # Auto-complete to the first match
                if cmd_matches:
                    buffer = cmd_matches[0]
                elif station_matches:
                    buffer = station_matches[0]

            elif char in ["\x03", "\x1b"]:  # Ctrl+C or ESC
                # ESC can produce \x1b followed by nothing if caught fast,
                # but arrows also start with \x1b. get_key handles sequences.
                if char == "\x1b":
                    return "q"
                return ""

            elif len(char) == 1:  # printable
                buffer += char

            # Update display with new buffer state
            live.update(get_display(buffer, cmd_matches or station_matches))


def handle_runtime_help_menu():
    """
    Show a colorful popup-style help menu using 'rich'.
    Uses the alternate screen buffer to avoid cluttering the console history.
    """
    from rich.align import Align
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    from radioactive.theme import get_current_theme

    theme = get_current_theme()
    console = Console()
    with console.screen():
        table = Table(box=None, expand=False, border_style="dim")
        table.add_column("Command", style=f"bold {theme.secondary}", justify="left")
        table.add_column("Description", style=theme.success, justify="left")

        # Helper to simplify adding rows
        def add(cmd, desc):
            table.add_row(cmd, desc)

        add("p", "Play/Pause current station")
        if TRACK_FEATURE:
            add("t / track  ", "Current track info")
        if INFO_FEATURE:
            add("i / info", "Station information")
        add("z / zenmode", "Minimalist station display")
        if RECORDING_FEATURE:
            add("r / record", "Record a station")
            add("rf / recordfile", "Specify a filename for the recording")
            add("rl / library", "Recording library (play, rename, delete, shazam)")

        add("f / fav", "Add station to favorite list")
        add("l / list", "Open favorite station selection menu")
        add("v <0-100>", "Set volume level")
        # add("v+ / v-", "Increase / Decrease volume level")

        if SEARCH_FEATURE:
            add("s / search", "Search for a new station")
        if CYCLE_FEATURE:
            add("n / next", "Play next result from search or favorites")
        if TRACK_FEATURE:
            add("a / auto", "Fetch track info every 10s")
        add("sz / shazam", "Identify current song using Shazam")
        add(". / settings", "Configure settings (Theme, Visualizer, Zen mode)")
        if TIMER_FEATURE:
            add("timer / sleep", "Set a sleep timer")

        add("q / quit", "Quit radioactive")
        add("b / background", "Run radioactive in the background")
        add("Any Text", "Fuzzy search & play from favorites/history")

        # Center the table within a panel
        help_panel = Panel(
            table,
            title=f"[{theme.title_style}]:radio: Available Runtime Commands[/{theme.title_style}]",
            subtitle="Press Enter to return",
            border_style=theme.border,
            expand=False,
            padding=(1, 4),
        )

        # Print the panel centered on the alternate screen
        console.print("\n" * 4)
        console.print(Align.center(help_panel))

        # Use console.input() to wait for Enter and avoid prompt capture
        try:
            console.input()
        except (EOFError, KeyboardInterrupt):
            pass


class AutoFetcher:
    def __init__(self):
        self.enabled = False
        self.thread = None
        self.last_song = ""
        self.target_url = ""

    def start(self, url):
        if self.enabled:
            return
        self.enabled = True
        self.target_url = url
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        log.info("Auto track info fetcher started (10s interval)")

    def stop(self):
        self.enabled = False
        if self.thread:
            # self.thread.join()
            self.thread = None
        log.info("Auto track info fetcher stopped")

    def toggle(self, url):
        if self.enabled:
            self.stop()
        else:
            self.start(url)

    def update_url(self, url):
        self.target_url = url
        self.last_song = ""

    def _run(self):
        while self.enabled:
            start_time = time.time()
            if self.target_url:
                current_song = get_current_track_name(self.target_url)
                if current_song and current_song != self.last_song:
                    station_info = get_global_station_info()
                    station_info["track"] = current_song
                    station_info["title"] = current_song
                    set_global_station_info(station_info)
                    station_name = station_info.get("name", "Unknown Station")

                    notification_title = f"Now Playing on {station_name}"
                    notification_message = f"🎶 {current_song}"

                    # Add extra info if available
                    codec = station_info.get("codec")
                    bitrate = station_info.get("bitrate")
                    if codec and bitrate:
                        notification_message += f"\n({codec} • {bitrate} kbps)"

                    handle_notification(notification_title, notification_message)
                    self.last_song = current_song

            # Calculate remaining time to sleep to keep a 10s interval
            elapsed = time.time() - start_time
            sleep_time = max(0, 10 - elapsed)
            time.sleep(sleep_time)


def handle_user_choice_from_search_result(handler, response) -> Tuple[str, str]:
    """
    Handle user selection from search results.
    """
    if not response:
        log.debug("No result found!")
        return None, None

    if len(response) == 1:
        # single station found
        log.debug("Exactly one result found")

        try:
            user_input = input("Want to play this station? Y/N: ")
        except EOFError:
            print()
            return None, None

        if user_input in ["y", "Y"]:
            log.debug("Playing UUID from single response")
            # Update global info - handled via helper to ensure UI sees it
            set_global_station_info(response[0])

            return handle_station_uuid_play(handler, response[0]["stationuuid"])
        else:
            log.debug("User chose not to play")
            return None, None
    else:
        # multiple station
        log.debug("Asking for user input")

        try:
            log.info("Type 'r' for a random station, 'n' to cycle through the list")
            user_input = input("Type the result ID to play: ")
        except EOFError:
            print()
            log.info("Returning to command prompt")
            return None, None

        try:
            if user_input in ["n", "N", "next"]:
                # user want's to play the first one and move on?
                user_input = 1
                log.debug("Next station requested, picking first one")

            if user_input in ["r", "R", "random"]:
                # pick a random integer within range (inclusive of last result)
                user_input = randint(1, len(response))
                log.debug(f"Random station id: {user_input}")
            # elif user_input in ["f", "F", "fuzzy"]:
            # fuzzy find all the stations, and return the selected station id
            # user_input = fuzzy_find(response)

            user_input = int(user_input) - 1  # because ID starts from 1
            if user_input in range(0, len(response)):
                target_response = response[user_input]
                log.debug(f"Selected: {target_response}")

                # saving global info
                set_global_station_info(target_response)

                return handle_station_uuid_play(handler, target_response["stationuuid"])
            else:
                log.error("Please enter an ID within the range")
                return None, None
        except ValueError:
            log.error("Please enter a valid ID number")
            return None, None
        except Exception as e:
            log.error(f"Error: {e}")
            return None, None


def handle_listen_keypress(
    alias,
    player,
    target_url,
    station_name,
    station_url,
    record_file_path,
    record_file,
    record_file_format,
    loglevel,
    handler=None,
    last_station=None,
    station_list=None,
    history=None,
    audio_player="ffplay",
    volume=80,
) -> None:
    """
    Listen for user input during playback to perform actions.
    Now with handler and station_list for runtime commands.
    """
    # log.info("Press '?' to see available commands\n")
    auto_fetcher = AutoFetcher()
    while True:
        try:
            user_input = handle_vim_style_prompt(alias, history)
            # print for logging/debugging consistency? No, user wants it clean.
        except EOFError:
            print()
            log.debug("Ctrl+D (EOF) detected. Exiting gracefully.")
            kill_background_ffplays()
            sys.exit(0)

        if RECORDING_FEATURE and user_input in ["r", "R", "record"]:
            if not target_url:
                log.error("Please select a station to record first.")
            else:
                process, outfile_path = handle_record(
                    target_url,
                    station_name,
                    record_file_path,
                    record_file,
                    record_file_format,
                    loglevel,
                )
                handle_recording_popup(process, outfile_path)
            continue

        elif RECORDING_FEATURE and user_input in ["rf", "RF", "recordfile"]:
            try:
                user_input = input("Enter output filename: ")
            except EOFError:
                print()
                log.debug("Ctrl+D (EOF) detected. Exiting gracefully.")
                kill_background_ffplays()
                sys.exit(0)

            # try to get extension from filename
            try:
                file_name_parts = user_input.split(".")
                if len(file_name_parts) > 1 and file_name_parts[-1] == "mp3":
                    log.debug("codec: force mp3")
                    # overwrite original codec with "mp3"
                    record_file_format = "mp3"
                    file_name = user_input.rsplit(".", 1)[
                        0
                    ]  # Handle filename with dots
                else:
                    if len(file_name_parts) > 1 and file_name_parts[-1] != "mp3":
                        log.warning("You can only specify mp3 as file extension.\n")
                        log.warning(
                            "Do not provide any extension to autodetect the codec.\n"
                        )
                    file_name = user_input
            except Exception:
                file_name = user_input

            if user_input.strip() != "":
                if not target_url:
                    log.error("Please select a station to record first.")
                else:
                    process, outfile_path = handle_record(
                        target_url,
                        station_name,
                        record_file_path,
                        file_name,
                        record_file_format,
                        loglevel,
                    )
                    handle_recording_popup(process, outfile_path)
            continue

        elif RECORDING_FEATURE and user_input in [
            "rl",
            "RL",
            "recordings",
            "library",
        ]:
            rec_name, rec_url = handle_recording_library()
            if rec_url:
                if player:
                    player.stop()
                    player.url = rec_url
                    player.play()
                else:
                    if audio_player == "vlc":
                        from radioactive.vlc import VLC

                        player = VLC(volume)
                        player.start(rec_url)
                    elif audio_player == "mpv":
                        from radioactive.mpv import MPV

                        player = MPV(volume)
                        player.start(rec_url)
                    else:
                        from radioactive.ffplay import Ffplay

                        player = Ffplay(rec_url, volume, loglevel)

                handle_current_play_panel("🎙️" + rec_name + "🎙️")
                station_name = rec_name
                station_url = rec_url
                target_url = rec_url
                auto_fetcher.update_url(target_url)
            continue

        if INFO_FEATURE and user_input in ["i", "I", "info"]:
            handle_show_station_info()
            continue

        elif user_input in ["z", "Z", "zenmode"]:
            current_vol = player.volume if player else volume
            handle_zen_mode(volume=current_vol)
            continue

        elif user_input.strip() in [
            ".",
            "settings",
            "setting",
            "set",
            "SETTINGS",
            "SETTING",
            "SET",
        ]:
            handle_settings()
            if station_name and station_name != "N/A":
                handle_current_play_panel(station_name)
            continue

        elif user_input in ["th", "TH", "theme", "THEME", "themes"]:
            handle_theme_selection()
            if station_name and station_name != "N/A":
                handle_current_play_panel(station_name)
            continue

        elif TIMER_FEATURE and user_input in ["timer", "sleep"]:
            try:
                duration_str = input("Enter sleep timer duration in minutes: ")
                duration = float(duration_str)
                if duration <= 0:
                    log.error("Duration must be positive")
                    continue

                log.info(f"Sleep timer set for {duration} minutes")

                def stop_playback():
                    log.info("\nSleep timer finished. Stopping playback...")
                    # We need to stop the player and exit.
                    # Since we are in a thread, we can't easily exit the main input loop cleanly
                    # without some signal, but sys.exit() or os._exit() should work strong enough.
                    if player:
                        player.stop()
                    kill_background_ffplays()
                    log.info("Exiting...")
                    os._exit(0)  # Force exit from thread

                t = threading.Timer(duration * 60, stop_playback)
                t.daemon = True  # Ensure it doesn't block exit if we quit manually
                t.start()

            except ValueError:
                log.error("Invalid number")
            except Exception as e:
                log.error(f"Error setting timer: {e}")

        elif user_input in ["f", "F", "fav"]:
            handle_add_to_favorite(alias, station_name, station_url)

        elif user_input in ["q", "Q", "quit"]:
            if player:
                player.stop()
            sys.exit(0)

        elif user_input in ["b", "B", "background"]:
            log.info("Moving to background...")
            try:
                pid = os.fork()
                if pid > 0:
                    # parent
                    log.info(
                        f"Radio-active is now running in the background. (PID: {pid})"
                    )
                    # No need to stop the player, the child inherits it?
                    # Actually ffplay is a separate process.
                    # We want the parent to exit and child to keep running.
                    # We should probably write the child PID to the PID file if we are using one.
                    from radioactive.paths import get_pid_path

                    with open(get_pid_path(), "w") as f:
                        f.write(str(pid))

                    sys.exit(0)
                else:
                    # child
                    os.setsid()
                    # Redirect standard file descriptors, keeping named refs for cleanup
                    sys.stdin.close()
                    _devnull_out = open(os.devnull, "w")
                    _devnull_err = open(os.devnull, "w")
                    sys.stdout = _devnull_out
                    sys.stderr = _devnull_err
                    # child should not listen to keypresses anymore
                    import signal

                    try:
                        signal.pause()
                    except (AttributeError, OSError):
                        while True:
                            time.sleep(100)
                    _devnull_out.close()
                    _devnull_err.close()
                    sys.exit(0)
            except AttributeError:
                log.error("Background mode is only supported on Unix-like systems")
            except Exception as e:
                log.error(f"Error while backgrounding: {e}")
            continue

        # elif user_input in ["w", "W"]:
        #     alias.generate_map()
        #     handle_favorite_table(alias)

        elif user_input in ["l", "L", "list"]:
            if handler and last_station:
                try:
                    res = handle_station_selection_menu(handler, last_station, alias)
                    new_station_name, new_target_url = res
                    if new_target_url:
                        if player:
                            if new_target_url == target_url:
                                log.info("Station is already playing!")
                                continue
                            player.stop()
                            player.url = new_target_url
                            player.play()
                        else:
                            # Initialize player
                            if audio_player == "vlc":
                                from radioactive.vlc import VLC

                                player = VLC(volume)
                                player.start(new_target_url)
                            elif audio_player == "mpv":
                                from radioactive.mpv import MPV

                                player = MPV(volume)
                                player.start(new_target_url)
                            else:
                                from radioactive.ffplay import Ffplay

                                player = Ffplay(new_target_url, volume, loglevel)
                        handle_current_play_panel(new_station_name)
                        # Save the new station as last played and add to history
                        handle_save_last_station(
                            last_station, new_station_name, new_target_url
                        )
                        handle_save_to_history(
                            history, new_station_name, new_target_url
                        )
                        # Update loop variables
                        station_name = new_station_name
                        station_url = new_target_url
                        target_url = new_target_url
                        auto_fetcher.update_url(target_url)
                except Exception as e:
                    log.error(f"Error selecting station: {e}")
            else:
                log.warning("Station selection menu unavailable")

        elif TRACK_FEATURE and user_input in ["t", "T", "track"]:
            handle_fetch_song_title(target_url)

        elif TRACK_FEATURE and user_input in ["a", "A", "auto"]:
            auto_fetcher.toggle(target_url)

        elif user_input in ["sz", "SZ", "shazam"]:
            handle_shazam(target_url)

        elif user_input in ["p", "P"]:
            if player:
                player.toggle()
            else:
                log.info("Nothing to play")

        elif SEARCH_FEATURE and user_input in ["s", "S", "search"]:
            if handler:
                try:
                    query = input("Enter station name to search: ")
                except EOFError:
                    continue

                if query.strip():
                    temp_station_list = handle_search_stations(
                        handler, query, limit=100, sort_by="votes", filter_with="none"
                    )
                    if temp_station_list:
                        station_list = temp_station_list
                        # Find valid station choice
                        try:
                            new_station_name, new_target_url = (
                                handle_user_choice_from_search_result(
                                    handler, station_list
                                )
                            )
                            if new_target_url:
                                if player:
                                    if new_target_url == target_url:
                                        log.info("Station is already playing!")
                                        continue
                                    # Stop current, switch
                                    player.stop()
                                    player.url = new_target_url
                                    player.play()
                                else:
                                    # Initialize player
                                    if audio_player == "vlc":
                                        from radioactive.vlc import VLC

                                        player = VLC(volume)
                                        player.start(new_target_url)
                                    elif audio_player == "mpv":
                                        from radioactive.mpv import MPV

                                        player = MPV(volume)
                                        player.start(new_target_url)
                                    else:
                                        from radioactive.ffplay import Ffplay

                                        player = Ffplay(
                                            new_target_url, volume, loglevel
                                        )
                                handle_current_play_panel(new_station_name)
                                # Save the new station as last played and add to history
                                handle_save_last_station(
                                    last_station, new_station_name, new_target_url
                                )
                                handle_save_to_history(
                                    history, new_station_name, new_target_url
                                )
                                # Update loop variables
                                station_name = new_station_name
                                station_url = new_target_url
                                target_url = new_target_url
                                auto_fetcher.update_url(target_url)
                        except SystemExit:
                            # handle_user_choice might try to exit on cancel
                            pass
            else:
                log.warning("Search unavailable (handler not initialized)")

        elif CYCLE_FEATURE and user_input in ["n", "N", "next"]:
            target_list = []
            source_type = ""

            # Prioritize search results if available
            if station_list and len(station_list) > 0:
                target_list = station_list
                source_type = "search"
            elif alias and alias.alias_map:
                target_list = alias.alias_map
                source_type = "favorite"

            if target_list:
                # Find current index
                current_info = get_global_station_info()
                current_uuid = current_info.get("stationuuid")
                current_url = current_info.get("url")  # for direct URLs

                current_index = -1

                # Try to find current station in the target list
                for idx, st in enumerate(target_list):
                    if source_type == "search":
                        if st.get("stationuuid") == current_uuid:
                            current_index = idx
                            break
                    elif source_type == "favorite":
                        # Favorites use uuid_or_url
                        val = st.get("uuid_or_url")
                        # Check against both uuid and url to be safe
                        if val == current_uuid or val == current_url:
                            current_index = idx
                            break
                        # Also check name as fallback
                        if st.get("name") == current_info.get("name"):
                            current_index = idx
                            break

                # Next index
                next_index = (current_index + 1) % len(target_list)

                # Try to play next valid station
                attempts = 0
                max_attempts = len(target_list)

                while attempts < max_attempts:
                    target_station = target_list[next_index]
                    log.debug(f"Switching to: {target_station.get('name')}")

                    # Determine how to play based on available info
                    # We need to simulate the "Selection" logic

                    try:
                        new_station_name = ""
                        new_target_url = ""

                        if source_type == "search":
                            # It's a full station object
                            set_global_station_info(target_station)
                            new_station_name, new_target_url = handle_station_uuid_play(
                                handler, target_station["stationuuid"]
                            )
                        else:
                            # Favorite entry: {'name':..., 'uuid_or_url':...}
                            # Construct a temporary info object for global state
                            uuid_or_url = target_station["uuid_or_url"]

                            temp_info = {
                                "name": target_station["name"],
                                "uuid_or_url": uuid_or_url,
                                # We might not know if it is a UUID or URL yet for sure without helper,
                                # but let's try to populate what we can
                            }

                            if "://" in uuid_or_url:
                                # Direct URL
                                temp_info["url"] = uuid_or_url
                                set_global_station_info(temp_info)
                                new_station_name = target_station["name"]
                                new_target_url = uuid_or_url
                                # Allow direct play without UUID handler
                            else:
                                # UUID
                                temp_info["stationuuid"] = uuid_or_url
                                set_global_station_info(temp_info)
                                new_station_name, new_target_url = (
                                    handle_station_uuid_play(handler, uuid_or_url)
                                )

                        # Check if we have a URL to play
                        if new_target_url:
                            if new_target_url == target_url:
                                # log.debug("Station already playing, but cycling next...")
                                # Actually, for 'next', if there's only 1 station, we should just stay
                                if len(target_list) == 1:
                                    log.info("Station is already playing!")
                                    break
                            if player:
                                player.stop()
                                player.url = new_target_url
                                player.play()
                            handle_current_play_panel(new_station_name)
                            # Save the new station as last played and add to history
                            handle_save_last_station(
                                last_station, new_station_name, new_target_url
                            )
                            handle_save_to_history(
                                history, new_station_name, new_target_url
                            )
                            station_url = new_target_url
                            station_name = new_station_name
                            target_url = new_target_url
                            auto_fetcher.update_url(target_url)
                            break
                        else:
                            raise Exception("Could not resolve station URL")

                    except Exception as e:
                        log.error(f"Failed to play {target_station.get('name')}: {e}")
                        next_index = (next_index + 1) % len(target_list)
                        attempts += 1

                if attempts >= max_attempts:
                    log.error("Could not play any station from the list")

            else:
                log.warning(
                    "Cycle/Next unavailable (no search results or favorites to cycle through)"
                )

        elif user_input == "v+":
            if player:
                new_vol = min(player.volume + 10, 100)
                player.set_volume(new_vol)
            else:
                log.info("Nothing is playing")

        elif user_input == "v-":
            if player:
                new_vol = max(player.volume - 10, 0)
                player.set_volume(new_vol)
            else:
                log.info("Nothing is playing")

        elif user_input.startswith("v "):
            if player:
                try:
                    vol_str = user_input.split(" ")[1].strip()
                    new_vol = int(vol_str)
                    if 0 <= new_vol <= 100:
                        player.set_volume(new_vol)
                    else:
                        log.error("Volume must be between 0 and 100")
                except Exception:
                    log.error("Invalid volume format. Use 'v 50'")
            else:
                log.info("Nothing is playing")

        elif user_input in ["?", "help"]:
            handle_runtime_help_menu()

        elif user_input.strip() != "":
            # Fuzzy match station from aliases or history if not a direct command
            # Try to see if it's a station name the user typed
            # log.info(f"Checking for station: {user_input}")
            try:
                name, url = handle_direct_play(alias, history, user_input)
                if url:
                    if url == target_url:
                        log.info("Station is already playing!")
                        continue
                    player.stop()
                    player.url = url
                    player.play()
                    handle_current_play_panel(name)
                    # Save the new station as last played and add to history
                    handle_save_last_station(last_station, name, url)
                    handle_save_to_history(history, name, url)
                    station_url = url
                    station_name = name
                    target_url = url
                    auto_fetcher.update_url(target_url)
            except SystemExit:
                # Direct play sys.exit(1) on failure, we want to stay in loop
                pass
            except Exception as e:
                log.debug(f"Error in fuzzy station search: {e}")
                log.warning(f"Unknown command or station: {user_input}")
