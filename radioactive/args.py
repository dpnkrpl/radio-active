import argparse
import sys

from zenlog import log

from radioactive.config import Configs

try:
    from radioactive.feature_flags import RECORDING_FEATURE, SEARCH_FEATURE
except ImportError:
    RECORDING_FEATURE = True
    SEARCH_FEATURE = True


# load default configs
def load_default_configs():
    # load config file and apply configs
    configs = Configs()
    default_configs = configs.load()
    return default_configs


class Parser:
    """Parse the command-line args and return result to the __main__"""

    def __init__(self):
        self.parser = None
        self.result = None
        self.defaults = load_default_configs()

        self.parser = argparse.ArgumentParser(
            description="Play any radio around the globe right from the CLI ",
            prog="radio-active",
            add_help=False,
        )

        self.parser.add_argument(
            "--version", action="store_true", dest="version", default=False
        )
        self.parser.add_argument(
            "--help",
            "-H",
            action="store_true",
            default=False,
            dest="help",
            help="Show help message",
        )

        self.parser.add_argument(
            "--search",
            "-S",
            action="store",
            dest="search_station_name",
            help="Specify a station name",
        )

        self.parser.add_argument(
            "--play",
            "-P",
            action="store",
            dest="direct_play",
            help="Specify a station from fav list or direct url",
        )

        self.parser.add_argument(
            "--url",
            "-u",
            action="store",
            dest="station_url",
            help="Specify a direct stream URL",
        )

        self.parser.add_argument(
            "--last",
            action="store_true",
            default=False,
            dest="play_last_station",
            help="Play last played station.",
        )

        self.parser.add_argument(
            "--random",
            action="store_true",
            default=False,
            dest="play_random_station",
            help="Play random station from fav list.",
        )

        self.parser.add_argument(
            "--uuid",
            "-U",
            action="store",
            dest="search_station_uuid",
            help="Specify a station UUID",
        )

        self.parser.add_argument(
            "--loglevel",
            action="store",
            default=self.defaults["loglevel"],
            dest="log_level",
            help="Specify log level",
        )

        self.parser.add_argument(
            "--country",
            "-C",
            action="store",
            dest="discover_country_code",
            help="Discover stations with country code",
        )

        self.parser.add_argument(
            "--tag",
            action="store",
            dest="discover_tag",
            help="Discover stations with tag",
        )

        self.parser.add_argument(
            "--state",
            action="store",
            dest="discover_state",
            help="Discover stations with state name",
        )

        self.parser.add_argument(
            "--language",
            action="store",
            dest="discover_language",
            help="Discover stations with state name",
        )
        self.parser.add_argument(
            "--limit",
            "-L",
            action="store",
            dest="limit",
            default=self.defaults["limit"],
            help="Limit of entries in discover table",
        )

        self.parser.add_argument(
            "--sort",
            action="store",
            dest="stations_sort_by",
            default=self.defaults["sort"],
            help="Sort stations",
        )

        self.parser.add_argument(
            "--filter",
            action="store",
            dest="stations_filter_with",
            default=self.defaults["filter"],
            help="Filter Results",
        )

        self.parser.add_argument(
            "--add",
            "-A",
            action="store_true",
            default=False,
            dest="new_station",
            help="Add an entry to your favorite station",
        )

        self.parser.add_argument(
            "--favorite",
            "-F",
            action="store",
            dest="add_to_favorite",
            help="Save current station to your favorite list",
        )

        self.parser.add_argument(
            "--list",
            action="store_true",
            dest="show_favorite_list",
            default=False,
            help="Show your favorite list in table format",
        )

        self.parser.add_argument(
            "--history",
            action="store_true",
            dest="show_history_list",
            default=False,
            help="Show recently played stations",
        )

        self.parser.add_argument(
            "--remove",
            action="store_true",
            default=False,
            dest="remove_fav_stations",
            help="Remove stations from favorite list",
        )

        self.parser.add_argument(
            "--flush",
            action="store_true",
            dest="flush",
            default=False,
            help="Flush your favorite list",
        )

        self.parser.add_argument(
            "--volume",
            "-V",
            action="store",
            dest="volume",
            default=self.defaults["volume"],
            type=int,
            choices=range(0, 101, 10),
            help="Volume to pass down to ffplay",
        )

        self.parser.add_argument(
            "--kill",
            "-K",
            action="store_true",
            dest="kill_ffplays",
            default=False,
            help="kill all the ffplay process initiated by radioactive",
        )

        if RECORDING_FEATURE:
            self.parser.add_argument(
                "--record",
                "-R",
                action="store_true",
                dest="record_stream",
                default=False,
                help="record a station and save as audio file",
            )

            self.parser.add_argument(
                "--filepath",
                action="store",
                dest="record_file_path",
                default=self.defaults["filepath"],
                help="specify the audio format for recording",
            )

            self.parser.add_argument(
                "--filename",
                "-N",
                action="store",
                dest="record_file",
                default="",
                help="specify the output filename of the recorded audio",
            )

            self.parser.add_argument(
                "--filetype",
                "-T",
                action="store",
                dest="record_file_format",
                default=self.defaults["filetype"],
                help="specify the audio format for recording. auto/mp3",
            )

            self.parser.add_argument(
                "--record-at",
                action="store",
                dest="record_at",
                default=None,
                help="Start recording at specific time (HH:MM) 24h",
            )

            self.parser.add_argument(
                "--duration",
                action="store",
                dest="record_duration",
                default=None,
                help="Duration of recording in minutes",
            )

        self.parser.add_argument(
            "--player",
            action="store",
            dest="audio_player",
            default=self.defaults["player"],
            help="specify the audio player to use. ffplay/vlc/mpv",
        )

        self.parser.add_argument(
            "--theme",
            action="store",
            dest="theme",
            default=self.defaults.get("theme", "default"),
            help="specify the UI color theme (default, cyberpunk, matrix, amber, nordic)",
        )

    def parse(self):
        self.result = self.parser.parse_args()
        if self.result is None:
            log.error("Could not parse the arguments properly")
            sys.exit(1)
        return self.result
