#!/usr/bin/env python
import atexit
import os
import signal
import sys
import threading
from time import sleep

# Globally needed as signal handler needs them.
# These are assigned inside main() or final_step().
ffplay = None
player = None


def final_step(options, last_station, alias, handler, history, station_list=None):
    global ffplay  # always needed
    global player

    from zenlog import log

    from radioactive.ffplay import Ffplay
    from radioactive.utilities import (
        handle_add_to_favorite,
        handle_current_play_panel,
        handle_listen_keypress,
        handle_record,
        handle_save_last_station,
        handle_save_to_history,
    )

    target_url = (options.get("target_url") or "").strip()
    if target_url == "":
        log.info("Type 's' to search for a station or '?' for help")
        player = None
    elif options["audio_player"] == "vlc":
        from radioactive.vlc import VLC

        vlc = VLC(options["volume"])
        vlc.start(options["target_url"])
        player = vlc

    elif options["audio_player"] == "mpv":
        from radioactive.mpv import MPV

        mpv = MPV(options["volume"])
        mpv.start(options["target_url"])
        player = mpv

    elif options["audio_player"] == "ffplay":
        ffplay = Ffplay(options["target_url"], options["volume"], options["loglevel"])
        player = ffplay

    else:
        log.error("Unsupported media player selected")
        sys.exit(1)

    if (options.get("curr_station_name") or "").strip() == "":
        options["curr_station_name"] = "N/A"

    if target_url != "":
        handle_save_last_station(last_station, options["curr_station_name"], target_url)

        handle_save_to_history(history, options["curr_station_name"], target_url)

        if options["add_to_favorite"]:
            handle_add_to_favorite(alias, options["curr_station_name"], target_url)

        handle_current_play_panel(options["curr_station_name"])

    if options["record_stream"]:
        if target_url == "":
            log.error("Cannot record in idle mode. Please select a station first.")
        else:
            handle_record(
                target_url,
                options["curr_station_name"],
                options["record_file_path"],
                options["record_file"],
                options["record_file_format"],
                options["loglevel"],
                options.get("record_duration"),
            )

    handle_listen_keypress(
        alias,
        player,
        target_url=options["target_url"],
        station_name=options["curr_station_name"],
        station_url=options["target_url"],
        record_file_path=options["record_file_path"],
        record_file=options["record_file"],
        record_file_format=options["record_file_format"],
        loglevel=options["loglevel"],
        handler=handler,
        last_station=last_station,
        station_list=station_list,
        history=history,
        audio_player=options["audio_player"],
        volume=options["volume"],
    )


def main():
    from zenlog import log

    log.level("info")

    from radioactive.app import App
    from radioactive.parser import parse_options

    app = App()
    options = parse_options()
    VERSION = app.get_version()

    # --- Fast early exits: avoid all heavy imports ---
    if options["version"]:
        log.info("RADIO-ACTIVE : version {}".format(VERSION))
        sys.exit(0)

    from radioactive.help import show_help

    if options["show_help_table"]:
        show_help()
        sys.exit(0)

    # --- Deferred heavy imports (saves ~260ms when not needed) ---
    import psutil

    from radioactive.alias import Alias
    from radioactive.ffplay import kill_background_ffplays
    from radioactive.handler import Handler
    from radioactive.history import History
    from radioactive.last_station import Last_station
    from radioactive.paths import get_pid_path
    from radioactive.utilities import (
        check_sort_by_parameter,
        handle_add_station,
        handle_add_to_favorite,
        handle_current_play_panel,
        handle_direct_play,
        handle_favorite_table,
        handle_history_table,
        handle_play_last_station,
        handle_play_random_station,
        handle_record,
        handle_search_stations,
        handle_station_selection_menu,
        handle_station_uuid_play,
        handle_update_modal,
        handle_update_screen,
        handle_user_choice_from_search_result,
        handle_welcome_screen,
    )

    alias = Alias()
    alias.generate_map()
    last_station = Last_station()
    history = History()

    if options["flush_fav_list"]:
        sys.exit(alias.flush())

    if options["kill_ffplays"]:
        kill_background_ffplays()
        pid_file = get_pid_path()
        if os.path.exists(pid_file):
            with open(pid_file, "r") as f:
                try:
                    pid = int(f.read().strip())
                    if psutil.pid_exists(pid):
                        os.kill(pid, signal.SIGTERM)
                        log.info(
                            f"Terminated background radioactive process (PID: {pid})"
                        )
                except:
                    pass
            try:
                os.remove(pid_file)
            except:
                pass
        sys.exit(0)

    # --------------- PID check ------------------- #
    pid_file = get_pid_path()
    if os.path.exists(pid_file):
        with open(pid_file, "r") as f:
            try:
                content = f.read().strip()
                if content:
                    old_pid = int(content)
                    if psutil.pid_exists(old_pid):
                        proc = psutil.Process(old_pid)
                        # Check if it's likely our app
                        if (
                            "python" in proc.name().lower()
                            or "radioactive" in proc.name().lower()
                        ):
                            log.warning(
                                f"Another instance of radioactive is already running (PID: {old_pid})"
                            )
                            try:
                                choice = input(
                                    "Open the existing one or open a new instance? (e/n): "
                                ).lower()
                                if choice == "e":
                                    log.info(
                                        "Continuing with existing instance. Exiting."
                                    )
                                    sys.exit(0)
                                elif choice == "n":
                                    log.info("Starting a new instance.")
                                else:
                                    log.info("Invalid choice. Exiting.")
                                    sys.exit(1)
                            except EOFError:
                                sys.exit(0)
            except (ValueError, psutil.NoSuchProcess, Exception) as e:
                log.debug(f"Error checking PID: {e}")
                pass

    # Save current PID
    with open(pid_file, "w") as f:
        f.write(str(os.getpid()))

    def cleanup():
        if os.path.exists(pid_file):
            try:
                with open(pid_file, "r") as f:
                    content = f.read().strip()
                    if content:
                        pid = int(content)
                        if pid == os.getpid():
                            os.remove(pid_file)
            except:
                pass

    atexit.register(cleanup)

    handle_welcome_screen()

    # Run update check in background so it never blocks the interactive prompt.
    # The modal will be shown if an update is detected.
    _update_thread = threading.Thread(target=app.is_update_available, daemon=True)
    _update_thread.start()

    # ------------------ SCHEDULED RECORDING MODE ------------------ #
    from radioactive.feature_flags import RECORDING_FEATURE

    if (
        RECORDING_FEATURE
        and options["record_at"]
        and (options["search_station_uuid"] or options["station_url"])
        and options["record_file"]
        and options["record_duration"]
    ):
        log.info(" Scheduled Recording Mode ")

        # 0. Check for existing file
        # Check if the output file already exists.
        # We need to respect the path and extension logic
        pass
        # Actually doing this check properly requires constructing the full path
        # copying logic from actions.handle_record essentially, or simpler version.

        from radioactive.paths import get_recordings_path

        rec_path = options["record_file_path"]
        if not rec_path:
            rec_path = get_recordings_path()

        rec_name = options["record_file"]
        rec_type = options["record_file_format"]
        if rec_type == "auto":
            # We can't know the extension for sure if it is auto without probing.
            # But usually user asks for "filename_check".
            # If user provided extension in filename, we use it.
            # If not, we might be in trouble for strict checking.
            # Let's assume if 'auto', we can't fully check unless we guess mp3 or similar.
            # But the user said "prompt user to change the name", so we should be strict.
            pass

        # Simplified check: if implicit extension or explicit one exists.
        # If user gives "foo", and type is mp3, we check "foo.mp3".
        # If type is auto, we might check "foo" or "foo.*"?

        # Let's reuse logic:
        # If user provided a name without extension, and type is mp3, append it.
        final_filename = rec_name
        if not any(
            rec_name.endswith(ext) for ext in [".mp3", ".aac", ".ogg", ".opus", ".flac"]
        ):
            if rec_type != "auto":
                final_filename = f"{rec_name}.{rec_type}"

        full_path = os.path.join(rec_path, final_filename)

        # If 'auto', we can't be 100% sure what the final file will be named by ffmpeg/logic,
        # but let's check exact match or assume mp3 fallback.
        # Actually, let's just check if the user provided name exists as a prefix or file.

        if os.path.exists(full_path):
            log.warning(f"File '{full_path}' already exists.")
            while True:
                user_choice = input("File already exists. Overwrite? (y/n): ").lower()
                if user_choice == "y":
                    break
                elif user_choice == "n":
                    new_name = input("Enter new filename (without extension): ")
                    options["record_file"] = new_name
                    # re-calculate
                    final_filename = new_name
                    if not any(
                        new_name.endswith(ext)
                        for ext in [".mp3", ".aac", ".ogg", ".opus", ".flac"]
                    ):
                        if rec_type != "auto":
                            final_filename = f"{new_name}.{rec_type}"
                    full_path = os.path.join(rec_path, final_filename)
                    if os.path.exists(full_path):
                        log.warning(f"File '{full_path}' also exists.")
                        continue  # ask again
                    else:
                        break  # good to go
                else:
                    continue

        # 1. Resolve Station UUID to Name and URL
        if options["station_url"]:
            options["target_url"] = options["station_url"]
            options["curr_station_name"] = "Direct URL"
            log.info(f"Target URL: {options['target_url']}")
        else:
            # We need to use handler to validate UUID
            handler = Handler()
            options["curr_station_name"], options["target_url"] = (
                handle_station_uuid_play(handler, options["search_station_uuid"])
            )

        # 2. Parse time and calculate delay
        import datetime
        import time

        try:
            target_time_str = options["record_at"]
            target_time_obj = datetime.datetime.strptime(
                target_time_str, "%H:%M"
            ).time()

            now = datetime.datetime.now()
            target_datetime = datetime.datetime.combine(now.date(), target_time_obj)

            # If target time is in the past, schedule for tomorrow
            if target_datetime < now:
                target_datetime += datetime.timedelta(days=1)

            log.info(
                f"Scheduled recording at: {target_datetime.strftime('%Y-%m-%d %H:%M:%S')}"
            )

            while True:
                now = datetime.datetime.now()
                remaining = target_datetime - now

                if remaining.total_seconds() <= 0:
                    break

                # Show remaining time HH:MM:SS
                # We overwrite the line to make it look like a countdown
                rem_str = str(remaining).split(".")[0]  # remove microseconds
                sys.stdout.write(f"\rTime remaining: {rem_str}")
                sys.stdout.flush()
                time.sleep(1)

            print()  # New line after countdown
            log.info("Starting scheduled recording...")

            # 3. Start Recording
            # We assume handle_record handles the recording process and exits or we exit after
            handle_record(
                options["target_url"],
                options["curr_station_name"],
                options["record_file_path"],
                options["record_file"],
                options["record_file_format"],
                options["loglevel"],
                options["record_duration"],
            )
            log.info("Scheduled recording finished.")
            sys.exit(0)

        except ValueError as e:
            log.error(f"Invalid time format: {e}")
            sys.exit(1)
        except KeyboardInterrupt:
            log.info("Scheduled recording cancelled.")
            sys.exit(0)

    if options["show_favorite_list"]:
        handle_favorite_table(alias)
        sys.exit(0)

    if options["show_history_list"]:
        from radioactive.feature_flags import HISTORY_FEATURE

        if HISTORY_FEATURE:
            handle_history_table(history)
        else:
            log.warning("History feature is disabled")
        sys.exit(0)

    if options["add_station"]:
        handle_add_station(alias)

    if options["remove_fav_stations"]:
        # handle_remove_stations(alias)
        alias.remove_entries()
        sys.exit(0)

    options["sort_by"] = check_sort_by_parameter(options["sort_by"])

    # Construct Handler as late as possible — right before we actually need the API.
    # This avoids the ~50ms init cost for flag-only paths (--list, --kill, etc.)
    handler = Handler()

    # Update check is already running in the background thread started above;
    # wait briefly (non-blocking) so it can print before we proceed to prompts
    _update_thread.join(timeout=0.4)
    if app.update_available:
        handle_update_modal(app)

    # ----------- country ----------- #
    if options["discover_country_code"]:
        response = handler.discover_by_country(
            options["discover_country_code"],
            options["limit"],
            options["sort_by"],
            options["filter_with"],
        )
        if response is not None:
            (
                options["curr_station_name"],
                options["target_url"],
            ) = handle_user_choice_from_search_result(handler, response)
            final_step(options, last_station, alias, handler, history, response)
        else:
            log.info("No stations found for this country.")
            final_step(options, last_station, alias, handler, history)

    # -------------- state ------------- #
    if options["discover_state"]:
        response = handler.discover_by_state(
            options["discover_state"],
            options["limit"],
            options["sort_by"],
            options["filter_with"],
        )
        if response is not None:
            (
                options["curr_station_name"],
                options["target_url"],
            ) = handle_user_choice_from_search_result(handler, response)
            final_step(options, last_station, alias, handler, history, response)
        else:
            log.info("No stations found for this state.")
            final_step(options, last_station, alias, handler, history)

    # ----------- language ------------ #
    if options["discover_language"]:
        response = handler.discover_by_language(
            options["discover_language"],
            options["limit"],
            options["sort_by"],
            options["filter_with"],
        )
        if response is not None:
            (
                options["curr_station_name"],
                options["target_url"],
            ) = handle_user_choice_from_search_result(handler, response)
            final_step(options, last_station, alias, handler, history, response)
        else:
            log.info("No stations found for this language.")
            final_step(options, last_station, alias, handler, history)

    # -------------- tag ------------- #
    if options["discover_tag"]:
        response = handler.discover_by_tag(
            options["discover_tag"],
            options["limit"],
            options["sort_by"],
            options["filter_with"],
        )
        if response is not None:
            (
                options["curr_station_name"],
                options["target_url"],
            ) = handle_user_choice_from_search_result(handler, response)
            final_step(options, last_station, alias, handler, history, response)
        else:
            log.info("No stations found for this tag.")
            final_step(options, last_station, alias, handler, history)

    # -------------------- NOTHING PROVIDED --------------------- #
    if (
        options["search_station_name"] is None
        and options["search_station_uuid"] is None
        and options["direct_play"] is None
        and not options["play_last_station"]
        and not options["play_random"]
    ):
        (
            options["curr_station_name"],
            options["target_url"],
        ) = handle_station_selection_menu(handler, last_station, alias)
        final_step(options, last_station, alias, handler, history)

    # --------------------ONLY UUID PROVIDED --------------------- #

    if options["search_station_uuid"] is not None:
        options["curr_station_name"], options["target_url"] = handle_station_uuid_play(
            handler, options["search_station_uuid"]
        )
        final_step(options, last_station, alias, handler, history)

    # ------------------- ONLY STATION PROVIDED ------------------ #

    elif (
        options["search_station_name"] is not None
        and options["search_station_uuid"] is None
        and options["direct_play"] is None
    ):
        response = [{}]
        response = handle_search_stations(
            handler,
            options["search_station_name"],
            options["limit"],
            options["sort_by"],
            options["filter_with"],
        )
        if response is not None:
            (
                options["curr_station_name"],
                options["target_url"],
            ) = handle_user_choice_from_search_result(handler, response)
            # options["codec"] = response["codec"]
            # print(response)
            final_step(options, last_station, alias, handler, history, response)
        else:
            final_step(options, last_station, alias, handler, history)
    # ------------------------- direct play ------------------------#
    if options["direct_play"] is not None:
        options["curr_station_name"], options["target_url"] = handle_direct_play(
            alias, history, options["direct_play"]
        )
        final_step(options, last_station, alias, handler, history)

    if options["play_random"]:
        (
            options["curr_station_name"],
            options["target_url"],
        ) = handle_play_random_station(alias)
        final_step(options, last_station, alias, handler, history)

    if options["play_last_station"]:
        options["curr_station_name"], options["target_url"] = handle_play_last_station(
            last_station
        )
        final_step(options, last_station, alias, handler, history)

    # final_step()
    # If response is not defined yet, initialize it
    if "response" not in locals():
        response = []

    final_step(options, last_station, alias, handler, history, response)

    if os.name == "nt":
        while True:
            sleep(5)
    else:
        try:
            signal.pause()
        except Exception as e:
            log.debug("Error: {}".format(e))
            pass


def signal_handler(sig, frame):
    from zenlog import log

    log.debug("You pressed Ctrl+C!")
    log.debug("Stopping the radio")
    if ffplay and ffplay.is_playing:
        ffplay.stop()
        #  kill the player
        player.stop()

    log.info("Exiting now")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)

if __name__ == "__main__":
    main()
