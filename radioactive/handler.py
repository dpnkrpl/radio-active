"""
This handler solely depends on pyradios module to communicate with our remote API
"""

import datetime
import json
import sys
import threading
from typing import Any, Dict, List, Optional, Union

from rich.console import Console
from rich.table import Table
from zenlog import log

from radioactive.filter import filter_expressions

try:
    from radioactive.feature_flags import MINIMAL_FEATURE
except ImportError:
    MINIMAL_FEATURE = False

# constants
DEFAULT_CACHE_RETENTION_DAYS = 3
BYTES_TO_MB_DIVISOR = 1024 * 1024

console = Console()


def trim_string(text: str, max_length: int = 40) -> str:
    """
    Trim a string to a maximum length and add ellipsis if needed.

    Args:
        text (str): The input text to be trimmed.
        max_length (int, optional): The maximum length of the trimmed string. Defaults to 40.

    Returns:
        str: The trimmed string, possibly with an ellipsis (...) if it was shortened.
    """
    if not isinstance(text, str):
        return str(text)

    if len(text) > max_length:
        return text[:max_length] + "..."
    return text


def print_table(
    response: List[Dict[str, Any]],
    columns: List[str],
    sort_by: str,
    filter_expression: str,
) -> List[Dict[str, Any]]:
    """
    Print the table applying the sort logic.

    Args:
        response (list): A list of data to be displayed in the table.
        columns (list): List of column specifications in the format "col_name:response_key@max_str".
        sort_by (str): The column by which to sort the table.
        filter_expression (str): Filter expression to apply strings.

    Returns:
        list: The original (or filtered) response data.
    """

    if MINIMAL_FEATURE:
        columns = [
            col
            for col in columns
            if all(x not in col for x in ["Tags", "Country", "Language"])
        ]
        if len(response) > 10:
            response = response[:10]

    if not response:
        log.error("No stations found")
        # sys.exit(1)
        return []

    # Apply filtering if needed
    if filter_expression.lower() != "none":
        response = filter_expressions(response, filter_expression)

        if not response:
            log.error("No stations found after filtering")
            # sys.exit(1)
            return []
    else:
        log.debug("Not filtering")

    if response:
        table = Table(
            show_header=True,
            header_style="magenta",
            expand=True,
            min_width=85,
            safe_box=True,
        )
        table.add_column("ID", justify="center")

        parsed_columns = []
        for col_spec in columns:
            parts = col_spec.split(":")
            col_name = parts[0]
            rest = parts[1].split("@")
            response_key = rest[0]
            max_str = int(rest[1])

            parsed_columns.append((col_name, response_key, max_str))
            table.add_column(col_name, justify="left")

        # Add the sort column if it's not already displayed (and not generic 'name' or 'random')
        if sort_by not in ["name", "random"]:
            table.add_column(sort_by, justify="left")

        for i, station in enumerate(response):
            row_data = [str(i + 1)]  # for ID

            for _, response_key, max_str in parsed_columns:
                val = station.get(response_key, "")
                row_data.append(trim_string(val, max_length=max_str))

            if sort_by not in ["name", "random"]:
                row_data.append(str(station.get(sort_by, "")))

            table.add_row(*row_data)

        console.print(table)
        return response
    else:
        log.info("No stations found")
        # Do not exit if no stations found, just return empty
        return []


class Handler:
    """
    radio-browser API handler. This module communicates with the underlying API via PyRadios.
    """

    def __init__(self):
        self.API = None
        self.response = None
        self.target_station = None

        # When RadioBrowser can not be initiated properly due to no internet (probably)
        try:
            import requests_cache
            from pyradios import RadioBrowser

            expire_after = datetime.timedelta(days=DEFAULT_CACHE_RETENTION_DAYS)
            session = requests_cache.CachedSession(
                cache_name="cache", backend="sqlite", expire_after=expire_after
            )
            self.API = RadioBrowser(session=session)
            self._country_map = None  # Lazy cache for country names -> codes
        except Exception as e:
            log.debug(f"Error initializing RadioBrowser: {e}")
            log.critical("Something is wrong with your internet connection")
            sys.exit(1)

    def _get_country_map(self) -> Dict[str, str]:
        """Lazy load and cache country mapping."""
        if self._country_map is None:
            try:
                log.debug("Fetching country list for cache...")
                countries = self.API.countries()
                self._country_map = {
                    c["name"].lower(): c["iso_3166_1"]
                    for c in countries
                    if "name" in c and "iso_3166_1" in c
                }
            except Exception as e:
                log.debug(f"Could not fetch country list: {e}")
                return {}
        return self._country_map

    def get_country_code(self, name: str) -> Optional[str]:
        """
        Get the ISO 3166-1 alpha-2 country code for a given country name (cached).
        """
        cmap = self._get_country_map()
        return cmap.get(name.lower())

    def validate_uuid_station(self) -> List[Dict[str, Any]]:
        """
        Validate that a station UUID search returned exactly one result and register a click.

        Returns:
            list: The response list containing the station details.
        """
        if self.response and len(self.response) >= 1:
            # We take the first one if multiple (unlikely for UUID but possible in theory)
            log.debug(json.dumps(self.response[0], indent=3))
            self.target_station = self.response[0]

            # register a valid click to increase its popularity (non-blocking)
            t = threading.Thread(
                target=self.vote_for_uuid,
                args=(self.target_station["stationuuid"],),
                daemon=True,
            )
            t.start()

            return self.response

        log.error("Station found by UUID is invalid or empty")
        sys.exit(1)

    # ---------------------------- NAME -------------------------------- #
    def search_by_station_name(
        self, name: str, limit: int, sort_by: str, filter_with: str
    ) -> List[Dict[str, Any]]:
        """
        Search and play a station by its name.

        Args:
            name (str): Station name to search for.
            limit (int): Max number of results.
            sort_by (str): Field to sort by.
            filter_with (str): Filter expression.

        Returns:
            list: List of found stations.
        """
        # Rename 'reversed' to avoid shadowing built-in
        is_reverse = sort_by != "name"

        try:
            response = self.API.search(
                name=name,
                name_exact=False,
                limit=limit,
                order=str(sort_by),
                reverse=is_reverse,
            )
            return print_table(
                response,
                ["Station:name@30", "Country:country@20", "Tags:tags@20"],
                sort_by=sort_by,
                filter_expression=filter_with,
            )
        except Exception as e:
            log.debug(f"Error in search_by_station_name: {e}")
            log.error("Something went wrong. please try again.")
            return []

    # ------------------------- UUID ------------------------ #
    def play_by_station_uuid(self, uuid: str) -> List[Dict[str, Any]]:
        """
        Search and play station by its stationuuid.

        Args:
            uuid (str): The UUID of the station.

        Returns:
            list: Confirmed station details.
        """
        try:
            self.response = self.API.station_by_uuid(uuid)
            return self.validate_uuid_station()
        except Exception as e:
            log.debug(f"Error in play_by_station_uuid: {e}")
            log.error("Something went wrong. please try again.")
            return []

    # -------------------------- COUNTRY ----------------------#
    def discover_by_country(
        self, country_code_or_name: str, limit: int, sort_by: str, filter_with: str
    ) -> List[Dict[str, Any]]:
        """
        Discover stations by country code or name.
        """
        is_reverse = sort_by != "name"

        # check if it is a code or name
        if len(country_code_or_name.strip()) == 2:
            # it's a code
            log.debug(f"Country code '{country_code_or_name}' provided")
            try:
                response = self.API.search(
                    countrycode=country_code_or_name,
                    limit=limit,
                    order=str(sort_by),
                    reverse=is_reverse,
                )
            except Exception as e:
                log.debug(f"Error searching by country code: {e}")
                log.error("Something went wrong. please try again.")
                sys.exit(1)
        else:
            # it's name
            log.debug(f"Country name '{country_code_or_name}' provided")
            code = self.get_country_code(country_code_or_name)
            if code:
                try:
                    response = self.API.search(
                        countrycode=code,
                        limit=limit,
                        country_exact=True,
                        order=str(sort_by),
                        reverse=is_reverse,
                    )
                except Exception as e:
                    log.debug(f"Error searching by country name: {e}")
                    log.error("Something went wrong. please try again.")
                    return []
            else:
                log.error(f"'{country_code_or_name}' is not a valid country name")
                return []

        # display and return result
        return print_table(
            response,
            [
                "Station:name@30",
                "State:state@20",
                "Tags:tags@20",
                "Language:language@20",
            ],
            sort_by,
            filter_with,
        )

    # ------------------- by state ---------------------

    def discover_by_state(
        self, state: str, limit: int, sort_by: str, filter_with: str
    ) -> List[Dict[str, Any]]:
        """Discover stations by state."""
        is_reverse = sort_by != "name"

        try:
            response = self.API.search(
                state=state, limit=limit, order=str(sort_by), reverse=is_reverse
            )
        except Exception as e:
            log.debug(f"Error discover_by_state: {e}")
            log.error("Something went wrong. please try again.")
            return []

        return print_table(
            response,
            [
                "Station:name@30",
                "Country:country@20",
                "State:state@20",
                "Tags:tags@20",
                "Language:language@20",
            ],
            sort_by,
            filter_with,
        )

    # -----------------by language --------------------

    def discover_by_language(
        self, language: str, limit: int, sort_by: str, filter_with: str
    ) -> List[Dict[str, Any]]:
        """Discover stations by language."""
        is_reverse = sort_by != "name"

        try:
            response = self.API.search(
                language=language, limit=limit, order=str(sort_by), reverse=is_reverse
            )
        except Exception as e:
            log.debug(f"Error discover_by_language: {e}")
            log.error("Something went wrong. please try again.")
            return []

        return print_table(
            response,
            [
                "Station:name@30",
                "Country:country@20",
                "Language:language@20",
                "Tags:tags@20",
            ],
            sort_by,
            filter_with,
        )

    # -------------------- by tag ---------------------- #
    def discover_by_tag(
        self, tag: str, limit: int, sort_by: str, filter_with: str
    ) -> List[Dict[str, Any]]:
        """Discover stations by tag."""
        is_reverse = sort_by != "name"

        try:
            response = self.API.search(
                tag=tag, limit=limit, order=str(sort_by), reverse=is_reverse
            )
        except Exception as e:
            log.debug(f"Error discover_by_tag: {e}")
            log.error("Something went wrong. please try again.")
            return []

        return print_table(
            response,
            [
                "Station:name@30",
                "Country:country@20",
                "Language:language@20",
                "Tags:tags@50",
            ],
            sort_by,
            filter_with,
        )

    # ---- Increase click count ------------- #
    def vote_for_uuid(self, uuid: str) -> Optional[Dict]:
        """Increase the click count for a station UUID."""
        try:
            result = self.API.click_counter(uuid)
            return result
        except Exception as e:
            log.debug(f"Something went wrong during increasing click count: {e}")
            return None
