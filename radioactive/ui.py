"""
UI components for radio-active using Rich.
"""

from rich import print
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from zenlog import log

from radioactive.theme import get_current_theme

# Global variable to store current station info for display
# This is shared state, ideally should be managed better, but keeping for compatibility
global_current_station_info = {}


def handle_welcome_screen() -> None:
    """Print the welcome screen panel."""
    theme = get_current_theme()
    welcome = Panel(
        """
        :radio: Play any radios around the globe right from this Terminal
        :smile: Author: Dipankar Pal
        :question: Type '--help' for more details on available commands
        :bug: Visit: https://github.com/dpnkrpl/radio-active
        :question: Press ? for help
        """,
        title=f"[{theme.title_style}]RADIOACTIVE[/{theme.title_style}]",
        border_style=theme.border,
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
        theme = get_current_theme()
        local_version = app.get_version()
        remote_version = app.get_remote_version()

        update_msg = (
            f"\t[blink]An update available, run [{theme.success}][italic]pipx upgrade radio-active"
            f"[/italic][/{theme.success}][/blink]\n"
        )

        # Add release notes for all missing versions if available
        release_notes = app.get_release_notes(local_version, remote_version)
        if release_notes:
            update_msg += f"\n[bold {theme.warning}]What's new since v{local_version}:[/bold {theme.warning}]\n{release_notes}"
        else:
            update_msg += f"\nSee all changes: https://github.com/dpnkrpl/radio-active/blob/main/CHANGELOG.md"

        update_panel = Panel(
            update_msg,
            border_style=theme.border,
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

        theme = get_current_theme()
        local_version = app.get_version()
        remote_version = app.get_remote_version()

        update_msg = (
            f"[bold {theme.success}]A new version of radio-active is available![/bold {theme.success}]\n\n"
            f"Current version: [{theme.warning}]v{local_version}[/{theme.warning}]\n"
            f"Latest version:  [bold {theme.success}]v{remote_version}[/bold {theme.success}]\n\n"
            f"To update, run:\n[italic]pipx upgrade radio-active[/italic]\n"
        )

        # Add release notes if available
        release_notes = app.get_release_notes(local_version, remote_version)
        if release_notes:
            update_msg += f"\n[bold {theme.warning}]What's new since v{local_version}:[/bold {theme.warning}]\n{release_notes}"
        else:
            update_msg += f"\nSee all changes: https://github.com/dpnkrpl/radio-active/blob/main/CHANGELOG.md"

        console = Console()
        with console.screen():
            info_panel = Panel(
                update_msg,
                title=f"[{theme.title_style}]🚀 Update Available[/{theme.title_style}]",
                subtitle="Press Enter to continue",
                border_style=theme.border,
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
    theme = get_current_theme()
    table = Table(
        show_header=True,
        header_style=theme.header_style,
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
    theme = get_current_theme()
    table = Table(
        show_header=True,
        header_style=theme.header_style,
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

        theme = get_current_theme()
        console = Console()
        with console.screen():
            table = Table(box=None, padding=(0, 2), show_header=False)
            table.add_column("Property", style=theme.secondary, justify="left")
            table.add_column("Value", style=theme.text)

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
                title=f"[{theme.title_style}]:radio: Station Information[/{theme.title_style}]",
                subtitle="Press Enter to return",
                border_style=theme.border,
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
    """Show an animated, dynamic 'Zen' audio visualizer display."""
    try:
        import math
        import random
        import select
        import sys
        import time

        from rich.align import Align
        from rich.console import Console
        from rich.live import Live
        from rich.panel import Panel
        from rich.text import Text

        theme = get_current_theme()
        console = Console()

        # Retrieve station metadata
        name = global_current_station_info.get("name")
        if not name or str(name).strip().upper() in ["N/A", "NONE", "UNKNOWN"]:
            display_name = "Unknown Station"
        else:
            display_name = str(name).strip()

        tags = global_current_station_info.get("tags")
        clean_tags = ""
        if tags and str(tags).strip() != "":
            clean_tags = str(tags).replace(",", " • ").strip()
            if len(clean_tags) > 65:
                clean_tags = clean_tags[:62] + "..."

        codec = global_current_station_info.get("codec")
        bitrate = global_current_station_info.get("bitrate")
        codec_info = ""
        if codec or bitrate:
            codec_info = f"{codec or ''} • {bitrate or ''} kbps".strip(" • ")

        num_bars = 28
        max_height = 6
        colors = (
            theme.visualizer_bars
            if theme.visualizer_bars
            else ["#00f5d4", "#00b4d8", "#7209b7", "#ffbd00", "#ff5400", "#ff0054"]
        )
        peaks = [0.0] * num_bars
        levels_current = [1.0] * num_bars

        def generate_frame(t: float) -> Panel:
            for i in range(num_bars):
                freq = 0.25 + (i / num_bars) * 1.2
                target = (
                    math.sin(t * 3.5 * freq + i * 0.4) * 2.2
                    + math.cos(t * 1.8 - i * 0.3) * 1.6
                    + random.uniform(0.2, 1.8)
                )
                target = max(0.2, min(float(max_height), target))
                levels_current[i] += (target - levels_current[i]) * 0.45
                val = levels_current[i]

                if val > peaks[i]:
                    peaks[i] = val
                else:
                    peaks[i] = max(0.0, peaks[i] - 0.22)

            content = Text(justify="center")
            content.append(
                f"\n✨ {display_name.upper()} ✨\n", style=theme.visualizer_title_style
            )
            if clean_tags:
                content.append(f"{clean_tags}\n", style="dim white")
            if codec_info:
                content.append(f"{codec_info}\n", style="italic dim white")
            content.append("\n")

            # Equalizer bars
            for r in range(max_height, 0, -1):
                row_text = Text()
                color = colors[r - 1]
                for i, val in enumerate(levels_current):
                    if val >= r:
                        row_text.append("█ ", style=color)
                    elif val >= r - 0.5:
                        row_text.append("▄ ", style=color)
                    elif int(peaks[i]) == r:
                        row_text.append("━ ", style=theme.text)
                    else:
                        row_text.append("  ")
                content.append_text(row_text)
                content.append("\n")

            # Stereo VU meters
            vu_left = min(8, max(0, int(levels_current[2] / max_height * 8)))
            vu_right = min(8, max(0, int(levels_current[5] / max_height * 8)))
            vu_bar_l = "▰" * vu_left + "▱" * (8 - vu_left)
            vu_bar_r = "▰" * vu_right + "▱" * (8 - vu_right)
            content.append(
                f"\nL: [{vu_bar_l}]   R: [{vu_bar_r}]\n",
                style=theme.visualizer_meter_style,
            )

            panel = Panel(
                Align.center(content),
                title=f"[{theme.title_style}]:radio: RADIOACTIVE ZEN MODE[/{theme.title_style}]",
                subtitle="[dim]Press [bold white]Enter[/bold white] or [bold white]q[/bold white] to return[/dim]",
                border_style=theme.border,
                padding=(1, 2),
                width=78,
            )
            return Align.center(panel, vertical="middle")

        is_tty = sys.stdin.isatty() and sys.stdout.isatty()
        if not is_tty:
            # Fallback for non-interactive / tests
            console.print(generate_frame(0.0))
            return

        old_settings = None
        fd = None
        if sys.platform != "win32":
            import termios
            import tty

            try:
                fd = sys.stdin.fileno()
                old_settings = termios.tcgetattr(fd)
                tty.setcbreak(fd)
            except Exception:
                old_settings = None

        try:
            with Live(
                generate_frame(0.0),
                console=console,
                screen=True,
                refresh_per_second=15,
            ) as live:
                start_time = time.time()
                while True:
                    t = time.time() - start_time
                    live.update(generate_frame(t))

                    # Check for exit keypress
                    key_pressed = False
                    if sys.platform == "win32":
                        import msvcrt

                        if msvcrt.kbhit():
                            key_pressed = True
                    else:
                        r, _, _ = select.select([sys.stdin], [], [], 0.05)
                        if r:
                            key_pressed = True

                    if key_pressed:
                        try:
                            if sys.platform == "win32":
                                msvcrt.getch()
                            else:
                                sys.stdin.read(1)
                        except Exception:
                            pass
                        break

                    time.sleep(0.04)

        finally:
            if old_settings is not None and fd is not None:
                import termios

                try:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                except Exception:
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

        theme = get_current_theme()
        console = Console()
        filename = os.path.basename(outfile_path)
        directory = os.path.dirname(outfile_path)

        with console.screen():
            table = Table(box=None, padding=(0, 2), show_header=False)
            table.add_column("Prop", style=theme.secondary, justify="right")
            table.add_column("Val", style=theme.text)

            table.add_row("File Name:", filename)
            table.add_row("Directory:", directory)
            table.add_row(
                "Status:",
                f"[blink][{theme.error}]● Recording ... [/{theme.error}][/blink]",
            )

            info_panel = Panel(
                table,
                title=f"[{theme.title_style}]RADIOACTIVE[/{theme.title_style}]",
                subtitle="Press Enter to STOP recording",
                border_style=theme.border,
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

        theme = get_current_theme()
        console = Console()
        with console.screen():
            table = Table(box=None, padding=(0, 2), show_header=False)
            table.add_column("Property", style=theme.secondary, justify="right")
            table.add_column("Value", style=theme.text)

            table.add_row("Title:", f"[bold]{title}[/bold]")
            table.add_row("Artist:", artist)
            table.add_row("Album:", album)
            table.add_row("Genre:", genre)
            table.add_row("Released:", released)
            table.add_row("Label:", label)
            table.add_row("Shazam URL:", f"[link={shazam_url}]{shazam_url}[/link]")

            info_panel = Panel(
                table,
                title=f"[{theme.title_style}]🎵 Song Identified[/{theme.title_style}]",
                subtitle="Press Enter to return",
                border_style=theme.border,
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

    theme = get_current_theme()
    panel_station_name = Text(display_name, justify="center", style=theme.accent)

    station_panel = Panel(
        panel_station_name,
        title="[blink]:radio:[/blink]",
        border_style=theme.border,
        width=72,
    )
    console = Console()
    console.print(station_panel)


def set_global_station_info(info: dict) -> None:
    """Helper to update global station info from other modules."""
    global global_current_station_info
    global_current_station_info = info


def get_global_station_info() -> dict:
    """Helper to get global station info."""
    return global_current_station_info
