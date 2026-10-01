from typing import Any, Dict, Optional

from zenlog import log

from radioactive.args import Parser


def parse_options() -> Dict[str, Any]:
    """
    Parse command-line arguments and return a dictionary of options.

    Returns:
        dict: A dictionary containing all the parsed options and their values.
    """
    parser = Parser()
    args = parser.parse()
    options: Dict[str, Any] = {}

    # ----------------- all the args ------------- #
    options["version"] = args.version
    options["show_help_table"] = args.help
    options["loglevel"] = args.log_level

    # check log levels
    if options["loglevel"] in ["info", "error", "warning", "debug"]:
        log.level(options["loglevel"])
    else:
        log.level("info")
        log.warning("Correct log levels are: error, warning, info(default), debug")

    # check is limit is a valid integer
    limit = args.limit
    options["limit"] = int(limit) if limit else 100
    log.debug("limit is set to: {}".format(limit))

    options["search_station_name"] = getattr(args, "search_station_name", None)
    options["search_station_uuid"] = args.search_station_uuid

    options["play_last_station"] = args.play_last_station
    options["direct_play"] = args.direct_play
    options["play_random"] = args.play_random_station

    options["sort_by"] = args.stations_sort_by
    options["filter_with"] = args.stations_filter_with

    options["discover_country_code"] = args.discover_country_code
    options["discover_state"] = args.discover_state
    options["discover_language"] = args.discover_language
    options["discover_tag"] = args.discover_tag

    options["add_station"] = args.new_station

    options["show_favorite_list"] = args.show_favorite_list
    options["show_history_list"] = getattr(args, "show_history_list", False)
    options["add_to_favorite"] = args.add_to_favorite
    options["flush_fav_list"] = args.flush
    options["remove_fav_stations"] = args.remove_fav_stations

    options["kill_ffplays"] = args.kill_ffplays

    options["record_stream"] = getattr(args, "record_stream", False)
    options["record_file"] = getattr(args, "record_file", "")
    options["record_file_format"] = getattr(args, "record_file_format", "mp3")
    options["record_file_path"] = getattr(args, "record_file_path", "")
    options["record_at"] = getattr(args, "record_at", None)
    options["record_duration"] = getattr(args, "record_duration", None)

    options["record_duration"] = getattr(args, "record_duration", None)

    options["station_url"] = getattr(args, "station_url", "")
    options["target_url"] = ""
    options["volume"] = args.volume
    options["audio_player"] = args.audio_player

    options["theme"] = getattr(args, "theme", "default")
    from radioactive.theme import set_current_theme

    set_current_theme(options["theme"])

    from radioactive.actions import set_desktop_notification_enabled, set_search_limit
    from radioactive.ui import (
        set_default_zen_style,
        set_zen_show_track,
        set_zen_show_visualizer,
        set_zen_show_volume,
        set_zen_timer,
    )

    if "limit" in options and options["limit"]:
        set_search_limit(options["limit"])

    if hasattr(parser, "defaults") and parser.defaults:
        defs = parser.defaults
        if "visualizer" in defs:
            set_default_zen_style(defs["visualizer"])
        if "zen_show_volume" in defs:
            set_zen_show_volume(
                defs["zen_show_volume"].lower() in ["true", "1", "yes", "on"]
            )
        if "zen_show_track" in defs:
            set_zen_show_track(
                defs["zen_show_track"].lower() in ["true", "1", "yes", "on"]
            )
        if "zen_show_visualizer" in defs:
            set_zen_show_visualizer(
                defs["zen_show_visualizer"].lower() in ["true", "1", "yes", "on"]
            )
        if "zen_timer" in defs:
            set_zen_timer(defs["zen_timer"])
        if "notification" in defs:
            set_desktop_notification_enabled(
                defs["notification"].lower() in ["true", "1", "yes", "on"]
            )

    return options
