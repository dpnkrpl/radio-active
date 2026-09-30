import json
import os
from typing import Dict, Optional

from zenlog import log

from radioactive.paths import get_history_path


class History:
    def __init__(self):
        self.history_path = get_history_path()
        self.history_list = []
        self.load()

    def load(self):
        try:
            if os.path.exists(self.history_path):
                with open(self.history_path, "r") as f:
                    self.history_list = json.load(f)
            else:
                self.history_list = []
        except (json.JSONDecodeError, Exception) as e:
            log.debug(f"Error loading history: {e}")
            self.history_list = []

    def append(self, station):
        """
        Add a station to history.
        station: dict with name, uuid, url keys mostly
        """
        curr_name = station.get("name", "").strip().lower()
        curr_uuid = (
            station.get("stationuuid") or station.get("uuid_or_url") or ""
        ).strip()

        # Deduplicate and bring to top
        new_list = []
        for s in self.history_list:
            prev_name = s.get("name", "").strip().lower()
            prev_uuid = (s.get("stationuuid") or s.get("uuid_or_url") or "").strip()

            if prev_name == curr_name:
                continue
            if prev_uuid and curr_uuid and prev_uuid == curr_uuid:
                continue

            new_list.append(s)

        self.history_list = new_list
        self.history_list.insert(0, station)

        # keep only last 20
        if len(self.history_list) > 20:
            self.history_list = self.history_list[:20]

        self.save()

    def save(self):
        """Atomic save of history file to prevent corruption."""
        try:
            temp_path = f"{self.history_path}.tmp"
            with open(temp_path, "w") as f:
                json.dump(self.history_list, f, indent=4)
            os.replace(temp_path, self.history_path)
        except Exception as e:
            log.warning(f"Could not save history: {e}")
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def get_list(self):
        return self.history_list

    def search(self, token: str) -> Optional[Dict]:
        """Search for a station in history by name, url, or uuid."""
        if not token:
            return None
        token = token.strip().lower()

        for entry in self.history_list:
            name = entry.get("name", "").strip().lower()
            url = entry.get("uuid_or_url", "").strip().lower()
            uuid = (entry.get("stationuuid") or "").strip().lower()

            if name == token or url == token or uuid == token:
                return entry
        return None
