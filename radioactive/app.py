"""
Version of the current program, (in development mode
it needs to be updated in every release)
and to check if an updated version available for the app or not
"""

import json
import sys

if sys.version_info >= (3, 8):
    from importlib import metadata
else:
    import importlib_metadata as metadata

# from zenlog import log


class App:
    def __init__(self):
        try:
            self.__VERSION__ = metadata.version("radio-active")
        except metadata.PackageNotFoundError:
            self.__VERSION__ = "4.1.0"  # change this on every update #
        self.pypi_api = "https://pypi.org/pypi/radio-active/json"
        self.remote_version = ""
        self.update_available = False

    def get_version(self):
        """get the version number as string"""
        return self.__VERSION__

    def get_remote_version(self):
        return self.remote_version

    def is_update_available(self):
        """Checks if the user is using an outdated version of the app,
        if any updates available inform user
        """

        try:
            import requests

            remote_data = requests.get(self.pypi_api)
            remote_data = remote_data.content.decode("utf8")
            remote_data = json.loads(remote_data)
            self.remote_version = remote_data["info"]["version"]

            # compare two version number
            tup_local = tuple(map(int, self.__VERSION__.split(".")))
            tup_remote = tuple(map(int, self.remote_version.split(".")))

            if tup_remote > tup_local:
                self.update_available = True
                return True
            self.update_available = False
            return False

        except Exception:
            # log.debug("Could not fetch remote version number")
            pass

    def get_release_notes(self, local_version, remote_version):
        """Fetch and parse release notes for all versions greater than local_version."""
        try:
            import requests

            url = "https://raw.githubusercontent.com/dpnkrpl/radio-active/main/CHANGELOG.md"
            response = requests.get(url)
            if response.status_code != 200:
                return None

            content = response.text
            lines = content.split("\n")

            collected_notes = []
            capturing = False
            current_version = None

            def version_tuple(v):
                return tuple(map(int, (v.split("."))))

            tup_local = version_tuple(local_version)
            # tup_remote = version_tuple(remote_version)

            for line in lines:
                if line.startswith("## "):
                    try:
                        v_str = line.replace("## ", "").strip()
                        tup_v = version_tuple(v_str)

                        if tup_v > tup_local:
                            capturing = True
                            current_version = v_str
                            collected_notes.append(f"\n[bold cyan]v{v_str}[/bold cyan]")
                        else:
                            capturing = False
                    except:
                        capturing = False
                elif capturing and line.strip():
                    collected_notes.append(line.strip())

            if collected_notes:
                return "\n".join(collected_notes)
            return None

        except Exception:
            return None
