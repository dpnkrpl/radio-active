"""
UI components for radio-active using Rich.
"""

from rich import print
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from zenlog import log

# Global variable to store current station info for display
# This is shared state, ideally should be managed better, but keeping for compatibility
global_current_station_info = {}


def handle_welcome_screen() -> None:
    """Print the welcome screen panel."""
    welcome = Panel(
        """
        :radio: Play any radios around the globe right from this Terminal
        :smile: Author: Dipankar Pal
        :question: Type '--help' for more details on available commands
        :bug: Visit: https://github.com/dpnkrpl/radio-active
        :question: Press ? for help
        """,
        title="[b]RADIOACTIVE[/b]",
        width=100,
        expand=False,
        safe_box=True,
    )
    print(welcome)


def handle_update_screen(app) -> None:
    """
    Check for updates and print a message if available.
    Used for non-modal background notification.

    Args:
        app: The App instance to check for updates.
    """
    if app.is_update_available():
        local_version = app.get_version()
        remote_version = app.get_remote_version()

        update_msg = (
            f"\t[blink]An update available, run [green][italic]pipx upgrade radio-active"
            f"[/italic][/green][/blink]\n"
        )

        # Add release notes for all missing versions if available
        release_notes = app.get_release_notes(local_version, remote_version)
        if release_notes:
            update_msg += f"\n[bold yellow]What's new since v{local_version}:[/bold yellow]\n{release_notes}"
        else:
            update_msg += f"\nSee all changes: https://github.com/dpnkrpl/radio-active/blob/main/CHANGELOG.md"

        update_panel = Panel(
            update_msg,
            width=100,
            expand=False,
        )
        print(update_panel)
    else:
        log.debug("Update not available")


def handle_update_modal(app) -> None:
    """
    Show a modal popup for update notification with release notes.

    Args:
        app: The App instance.
    """
    try:
        from rich.align import Align
        from rich.console import Console
        from rich.panel import Panel

        local_version = app.get_version()
        remote_version = app.get_remote_version()

        update_msg = (
            f"[bold green]A new version of radio-active is available![/bold green]\n\n"
            f"Current version: [yellow]v{local_version}[/yellow]\n"
            f"Latest version:  [bold green]v{remote_version}[/bold green]\n\n"
            f"To update, run:\n[italic]pipx upgrade radio-active[/italic]\n"
        )

        # Add release notes if available
        release_notes = app.get_release_notes(local_version, remote_version)
        if release_notes:
            update_msg += f"\n[bold yellow]What's new since v{local_version}:[/bold yellow]\n{release_notes}"
        else:
            update_msg += f"\nSee all changes: https://github.com/dpnkrpl/radio-active/blob/main/CHANGELOG.md"

        console = Console()
        with console.screen():
            info_panel = Panel(
                update_msg,
                title="[bold white]🚀 Update Available[/bold white]",
                subtitle="Press Enter to continue",
                border_style="green",
                padding=(1, 4),
                width=100,
                expand=False,
            )

            # Center the panel visually
            console.print("\n" * 4)
            console.print(Align.center(info_panel))

            try:
                console.input()
            except (EOFError, KeyboardInterrupt):
                pass

    except Exception as e:
        log.debug(f"Error in update modal: {e}")


def handle_favorite_table(alias) -> None:
    """
    Print the user's favorite list in a table.

    Args:
        alias: The Alias instance containing the favorite map.
    """
    table = Table(
        show_header=True,
        header_style="bold magenta",
        width=100,
        safe_box=False,
        expand=False,
    )
    table.add_column("Station", justify="left")
    table.add_column("URL / UUID", justify="left")

    if len(alias.alias_map) > 0:
        for entry in alias.alias_map:
            table.add_row(entry["name"], entry["uuid_or_url"])
        print(table)
        log.info(f"Your favorite stations are saved in {alias.alias_path}")
    else:
        log.info("You have no favorite station list")


def handle_history_table(history) -> None:
    """
    Print the user's history list in a table.

    Args:
        history: The History instance containing the history list.
    """
    table = Table(
        show_header=True,
        header_style="bold magenta",
        width=100,
        safe_box=False,
        expand=False,
    )
    table.add_column("Station", justify="left")
    table.add_column("URL / UUID", justify="left")

    if len(history.history_list) > 0:
        for entry in history.history_list:
            table.add_row(entry["name"], entry["uuid_or_url"])
        print(table)
        log.info(f"Your history is saved in {history.history_path}")
    else:
        log.info("You have no history")


def handle_show_station_info() -> None:
    """Show important information regarding the current station in an alternate screen (Modal)."""
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table

        console = Console()
        with console.screen():
            table = Table(box=None, padding=(0, 2), show_header=False)
            table.add_column("Property", style="cyan", justify="left")
            table.add_column("Value", style="white")

            # Map internal keys to display labels
            fields = [
                ("Name", "name"),
                ("UUID", "stationuuid"),
                ("Stream URL", "url"),
                ("Website", "homepage"),
                ("Country", "country"),
                ("Language", "language"),
                ("Tags", "tags"),
                ("Codec", "codec"),
                ("Bitrate", "bitrate"),
            ]

            for label, key in fields:
                val = str(global_current_station_info.get(key, "N/A"))
                if val.strip() == "" or val == "None":
                    val = "N/A"
                table.add_row(f"{label}:", val)

            info_panel = Panel(
                table,
                title="[bold white]:radio: Station Information[/bold white]",
                subtitle="Press Enter to return",
                border_style="white",
                padding=(1, 4),
                expand=False,
            )

            console.print("\n" * 3)
            console.print(info_panel, justify="center")

            try:
                console.input()
            except (EOFError, KeyboardInterrupt):
                pass

    except Exception as e:
        log.error(f"No station information available: {e}")


def handle_zen_mode() -> None:
    """Show a minimalist 'Zen' display of the current station."""
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text

        # Beautiful Zen emojis
        emojis = ["✨", "🧘", "🌊", "🍃", "🌙", "☁️", "🎵", "🎧"]
        import random

        from rich.align import Align

        icon = random.choice(emojis)

        console = Console()
        with console.screen():
            # defensive retrieval of the name
            name = global_current_station_info.get("name")
            if not name or str(name).strip().upper() in ["N/A", "NONE", "UNKNOWN"]:
                # fallback, check if we have it anywhere else?
                display_name = "Unknown Station"
            else:
                display_name = str(name).strip()

            # Create a stylized station name
            zen_text = Text(justify="center")

            # Beautiful Wave Decoration
            wave = " ▂ ▃ ▅ ▆ █ █ ▆ ▅ ▃ ▂ "
            # zen_text.append(f"\n{wave}\n\n", style="bold white")

            zen_text.append(f"{icon} ", style="bold yellow")
            zen_text.append(display_name.upper(), style="bold white")
            zen_text.append(f" {icon}\n", style="bold yellow")

            # Add more data if available
            tags = global_current_station_info.get("tags")
            if tags and str(tags).strip() != "":
                clean_tags = str(tags).replace(",", " • ").strip()
                if len(clean_tags) > 70:
                    clean_tags = clean_tags[:67] + "..."
                zen_text.append(f"\n{clean_tags}\n", style="dim white")

            codec = global_current_station_info.get("codec")
            bitrate = global_current_station_info.get("bitrate")
            if codec or bitrate:
                info_line = f"\n{codec or ''} • {bitrate or ''} kbps".strip(" • ")
                zen_text.append(info_line, style="italic dim white")

            # zen_text.append(f"\n\n{wave}\n", style="bold white")

            zen_panel = Panel(
                zen_text,
                title="[bold white]RADIOACTIVE[/bold white]",
                subtitle="Press Enter to return",
                border_style="bold white",
                padding=(2, 4),
                width=100,
                expand=False,
            )

            # Center vertically with some newlines
            console.print("\n" * 8)
            console.print(Align.center(zen_panel))

            try:
                input()
            except (EOFError, KeyboardInterrupt):
                pass

    except Exception as e:
        log.error(f"Error in zen mode: {e}")


def handle_recording_popup(process, outfile_path) -> None:
    """Show a static recording info panel in an alternate screen (Popup)."""
    if not process:
        return

    try:
        import os

        from rich.align import Align
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table

        console = Console()
        filename = os.path.basename(outfile_path)
        directory = os.path.dirname(outfile_path)

        with console.screen():
            table = Table(box=None, padding=(0, 2), show_header=False)
            table.add_column("Prop", style="cyan", justify="right")
            table.add_column("Val", style="white")

            table.add_row("File Name:", filename)
            table.add_row("Directory:", directory)
            table.add_row(
                "Status:", "[blink][bold red]● Recording ... [/bold red][/blink]"
            )

            info_panel = Panel(
                table,
                title="[bold white]RADIOACTIVE[/bold white]",
                subtitle="Press Enter to STOP recording",
                border_style="white",
                padding=(1, 4),
                width=100,
                expand=False,
            )

            # Center the panel visually
            console.print("\n" * 8)
            console.print(Align.center(info_panel))

            while process.poll() is None:
                try:
                    # Wait for Enter to stop
                    input()
                    try:
                        # send 'q' to ffmpeg to save and quit nicely
                        process.stdin.write(b"q")
                        process.stdin.flush()
                    except:
                        process.terminate()
                    process.wait()
                    break
                except (EOFError, KeyboardInterrupt):
                    process.terminate()
                    process.wait()
                    break

        # finalize UI after stop or process ends
        # log.info(f"Recording saved at: {outfile_path}")

    except Exception as e:
        log.error(f"Error in recording popup: {e}")


def handle_shazam_popup(result: dict) -> None:
    """Show identified song information in an alternate screen (Modal)."""
    if not result or not result.get("track"):
        log.error("No track information available to display.")
        return

    try:
        from rich.align import Align
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table

        track = result.get("track")
        title = track.get("title", "N/A")
        artist = track.get("subtitle", "N/A")
        genre = track.get("genres", {}).get("primary", "N/A")
        shazam_url = track.get("url", "N/A")

        # Extract album and release year from sections if available
        album = "N/A"
        released = "N/A"
        label = "N/A"

        sections = track.get("sections", [])
        for section in sections:
            if section.get("type") == "SONG":
                metadata = section.get("metadata", [])
                for item in metadata:
                    if item.get("title") == "Album":
                        album = item.get("text", "N/A")
                    elif item.get("title") == "Released":
                        released = item.get("text", "N/A")
                    elif item.get("title") == "Label":
                        label = item.get("text", "N/A")

        console = Console()
        with console.screen():
            table = Table(box=None, padding=(0, 2), show_header=False)
            table.add_column("Property", style="cyan", justify="right")
            table.add_column("Value", style="white")

            table.add_row("Title:", f"[bold]{title}[/bold]")
            table.add_row("Artist:", artist)
            table.add_row("Album:", album)
            table.add_row("Genre:", genre)
            table.add_row("Released:", released)
            table.add_row("Label:", label)
            table.add_row("Shazam URL:", f"[link={shazam_url}]{shazam_url}[/link]")

            info_panel = Panel(
                table,
                title="[bold white]🎵 Song Identified[/bold white]",
                subtitle="Press Enter to return",
                border_style="white",
                padding=(1, 4),
                width=100,
                expand=False,
            )

            # Center the panel visually
            console.print("\n" * 6)
            console.print(Align.center(info_panel))

            try:
                console.input()
            except (EOFError, KeyboardInterrupt):
                pass

    except Exception as e:
        log.error(f"Error in shazam popup: {e}")


def handle_current_play_panel(curr_station_name: str = "") -> None:
    """
    Print the currently playing station panel and sync station name state.

    Args:
        curr_station_name (str): Name of the station.
    """
    # Ensure the global state is always updated with the active station name
    if curr_station_name and curr_station_name.strip() != "":
        # Update the name to ensure sync even if previous station name existed
        global_current_station_info["name"] = curr_station_name

    # Truncate to 30 chars
    display_name = curr_station_name
    if len(display_name) > 30:
        display_name = display_name[:27] + "..."

    panel_station_name = Text(display_name, justify="center")

    station_panel = Panel(panel_station_name, title="[blink]:radio:[/blink]", width=72)
    console = Console()
    console.print(station_panel)


def set_global_station_info(info: dict) -> None:
    """Helper to update global station info from other modules."""
    global global_current_station_info
    global_current_station_info = info


def get_global_station_info() -> dict:
    """Helper to get global station info."""
    return global_current_station_info
