"""
Configuration management for radio-active.
Handles loading, saving, and managing user configurations.
"""

import configparser
import getpass
import os
import sys
from typing import Any, Dict, Optional

from zenlog import log


def save_config_option(key: str, value: str) -> None:
    """
    Save or update a single configuration option in the config file.
    """
    from radioactive.paths import get_config_path

    file_path = get_config_path()
    config = configparser.ConfigParser()

    try:
        if os.path.exists(file_path):
            config.read(file_path)

        if not config.has_section("AppConfig"):
            config.add_section("AppConfig")

        config.set("AppConfig", key, str(value))

        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w") as config_file:
            config.write(config_file)

        log.debug(f"Saved config option '{key} = {value}' to {file_path}")
    except Exception as e:
        log.error(f"Error saving config option '{key}': {e}")


def write_a_sample_config_file() -> None:
    """
    Create a sample configuration file with default settings.
    Checks for the XDG config path and writes the file there.
    """
    config = configparser.ConfigParser()
    from radioactive.paths import get_recordings_path, get_user_home

    # Add sections and key-value pairs
    config["AppConfig"] = {
        "loglevel": "info",
        "limit": "100",
        "sort": "votes",
        "filter": "none",
        "volume": "80",
        "filepath": os.path.join("{home}", "radioactive", "recordings"),
        "filetype": "mp3",
        "player": "ffplay",
        "theme": "default",
        "visualizer": "0",
        "zen_show_volume": "true",
        "zen_show_track": "true",
        "zen_show_visualizer": "true",
        "zen_timer": "15",
    }

    try:
        from radioactive.paths import get_config_path

        # Specify the file path
        file_path = get_config_path()

        # Write the configuration to the file
        with open(file_path, "w") as config_file:
            config.write(config_file)

        log.info(f"A sample default configuration file added at: {file_path}")

    except Exception as e:
        log.error(f"Error writing the configuration file: {e}")


class Configs:
    """
    Class to handle loading and parsing of the configuration file.
    """

    def __init__(self):
        from radioactive.paths import get_config_path

        self.config_path = get_config_path()
        self.config: Optional[configparser.ConfigParser] = None

    def load(self) -> Dict[str, str]:
        """
        Load the configuration file and return options as a dictionary.

        Returns:
            dict: The configuration options.
        """
        self.config = configparser.ConfigParser()

        try:
            self.config.read(self.config_path)
            options: Dict[str, str] = {}

            # Helper to safely get config values with defaults if section missing
            def get_option(key: str, default: str = "") -> str:
                try:
                    return self.config.get("AppConfig", key)
                except (configparser.NoSectionError, configparser.NoOptionError):
                    return default

            options["volume"] = get_option("volume", "80")
            options["loglevel"] = get_option("loglevel", "info")
            options["sort"] = get_option("sort", "votes")
            options["filter"] = get_option("filter", "none")
            options["limit"] = get_option("limit", "100")
            from radioactive.paths import get_recordings_path, get_user_home

            options["filepath"] = get_option("filepath", get_recordings_path())

            if "{user}" in options["filepath"]:
                options["filepath"] = options["filepath"].replace(
                    "{user}", getpass.getuser()
                )

            if "{home}" in options["filepath"]:
                options["filepath"] = options["filepath"].replace(
                    "{home}", get_user_home()
                )

            options["filepath"] = os.path.expanduser(options["filepath"])

            options["filetype"] = get_option("filetype", "mp3")
            options["player"] = get_option("player", "ffplay")
            options["theme"] = get_option("theme", "default")
            options["visualizer"] = get_option("visualizer", "0")
            options["zen_show_volume"] = get_option("zen_show_volume", "true")
            options["zen_show_track"] = get_option("zen_show_track", "true")
            options["zen_show_visualizer"] = get_option("zen_show_visualizer", "true")
            options["zen_timer"] = get_option("zen_timer", "15")

            return options

        except Exception as e:
            log.error(f"Something went wrong while parsing the config file: {e}")
            # write the example config file
            write_a_sample_config_file()
            log.info("Re-run radioactive")
            sys.exit(1)
