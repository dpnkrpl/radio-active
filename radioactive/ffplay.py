"""
Module for handling FFplay process management to play radio streams.
"""

import os
import signal
import subprocess
import sys
import threading
from shutil import which
from time import sleep
from typing import Any, List, Optional

import psutil
from zenlog import log


def kill_background_ffplays() -> None:
    """
    Kill all background 'ffplay' processes started by this user.
    Optimized to use faster platform-specific tools when available.
    """
    try:
        if sys.platform != "win32":
            # Fast path for Unix-like systems
            # -x ensures exact match for process name 'ffplay'
            subprocess.run(
                ["pkill", "-x", "ffplay"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return
    except Exception:
        pass

    # Fallback to psutil if pkill fails or on Windows
    all_processes = psutil.process_iter(attrs=["pid", "name"])
    for process in all_processes:
        try:
            if process.info["name"] == "ffplay":
                pid = process.info["pid"]
                p = psutil.Process(pid)
                p.terminate()
                log.debug(f"Terminated ffplay process with PID {pid}")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass


class Ffplay:
    """
    Wrapper class to manage the FFplay process for audio playback.
    """

    def __init__(self, URL: str, volume: int, loglevel: str):
        self.program_name = "ffplay"
        self.url = URL
        self.volume = volume
        self.loglevel = loglevel
        self.is_playing = False
        self.process: Optional[subprocess.Popen] = None
        self.exe_path: Optional[str] = None
        self.is_running = False

        self._check_ffplay_installation()
        self.start_process()

    def _check_ffplay_installation(self) -> None:
        """Check if ffplay is installed and available in PATH."""
        self.exe_path = which(self.program_name)
        if self.exe_path is None:
            log.critical("FFplay not found, install it first please")
            sys.exit(1)

    def _construct_ffplay_commands(self) -> List[str]:
        """Construct the command line arguments for ffplay."""
        # Ensure volume is within valid range (0-100) though ffplay accepts 0-100
        # Actually ffplay volume is 0-100

        if self.exe_path is None:
            raise RuntimeError("FFplay executable path is not set")

        ffplay_commands = [self.exe_path, "-volume", f"{self.volume}", "-vn", self.url]

        if self.loglevel == "debug":
            ffplay_commands.extend(["-loglevel", "error"])
        else:
            ffplay_commands.extend(["-loglevel", "error", "-nodisp"])

        return ffplay_commands

    def start_process(self) -> None:
        """Start the ffplay process."""
        try:
            ffplay_commands = self._construct_ffplay_commands()
            self.process = subprocess.Popen(
                ffplay_commands,
                shell=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                text=True,
            )

            self.is_running = True
            self.is_playing = True
            self._start_error_thread()

        except Exception as e:
            log.error(f"Error while starting radio: {e}")
            self.is_playing = False

    def _start_error_thread(self) -> None:
        """Start a thread to monitor stderr for errors."""
        error_thread = threading.Thread(target=self._check_error_output)
        error_thread.daemon = True
        error_thread.start()

    def _check_error_output(self) -> None:
        """Monitor stderr for errors."""
        import re

        if not self.process or not self.process.stderr:
            return

        while self.is_running and self.process and self.process.stderr:
            try:
                stderr_result = self.process.stderr.readline()
                if not stderr_result:
                    if self.process and self.process.poll() is not None:
                        if self.process.poll() != 0 and self.is_running:
                            self._handle_error("")
                            self.is_running = False
                            self.stop()
                        break
                    sleep(0.1)
                    continue

                # Strip ANSI escape sequences
                clean_msg = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", stderr_result).strip()

                # If purely whitespace, escape codes, or macOS CoreAudio escape warnings, ignore
                if not clean_msg or "Dropped Escape call" in clean_msg:
                    log.debug(f"ffplay non-fatal stderr: {stderr_result.strip()}")
                    continue

                # Check if ffplay is still actively running
                sleep(0.1)
                if self.process and self.process.poll() is None:
                    # Process is still alive and playing fine
                    log.debug(
                        f"ffplay non-fatal message (playback continuing): {clean_msg}"
                    )
                    continue

                # Process has actually exited with error
                if self.is_running:
                    self._handle_error(clean_msg)
                    self.is_running = False
                    self.stop()
                    break

            except ValueError:
                # ValueError: I/O operation on closed file.
                break
            except Exception as e:
                log.debug(f"Error checking ffplay stderr: {e}")
                break

    def _handle_error(self, stderr_result: str) -> None:
        """Log the error message."""
        print()
        log.error("Could not connect to the station/stream")
        if stderr_result:
            try:
                log.debug(stderr_result)
                parts = stderr_result.split(": ")
                if len(parts) > 1:
                    log.error(parts[1].strip())
                else:
                    log.error(stderr_result.strip())
            except Exception as e:
                log.debug(f"Error parsing stderr: {e}")

    def terminate_parent_process(self) -> None:
        """Signal the parent process (main app) to terminate."""
        parent_pid = os.getppid()
        try:
            os.kill(parent_pid, signal.SIGINT)
        except Exception as e:
            log.debug(f"Could not kill parent process: {e}")

    def is_active(self) -> bool:
        """Check if the ffplay process is currently active/running (fast)."""
        if not self.process:
            return False

        return self.process.poll() is None

    def play(self) -> None:
        """Resume or start playback."""
        if not self.is_playing:
            self.start_process()

    def stop(self) -> None:
        """Stop playback and terminate the process."""
        if self.is_playing and self.process:
            self.is_running = False  # Stop the error thread loop
            try:
                self.process.terminate()
                try:
                    self.process.wait(timeout=0.2)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=0.2)

                log.debug("Radio playback stopped successfully")
            except Exception as e:
                log.error(f"Error while stopping radio: {e}")
            finally:
                self.is_playing = False
                self.process = None
        else:
            log.debug("Radio is not currently playing")

    def toggle(self) -> None:
        """Toggle playback state."""
        if self.is_playing:
            log.debug("Stopping the ffplay process")
            self.stop()
        else:
            log.debug("Starting the ffplay process")
            self.start_process()

    def set_volume(self, volume: int) -> None:
        """Update the volume level and restart playback if active."""
        self.volume = volume
        log.info(f"Volume set to {self.volume}")
        if self.is_playing:
            log.debug("Restarting ffplay with new volume")
            # We don't want to kill the parent process if stop() fails
            self.stop()
            self.start_process()
