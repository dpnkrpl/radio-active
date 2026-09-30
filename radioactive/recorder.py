import subprocess

from zenlog import log


def record_audio_auto_codec(input_stream_url):
    """Detect the audio codec of a stream and map it to a standard extension."""
    # Standard mapping of codec_name to file extension
    CODEC_MAP = {
        "aac": "aac",
        "mp3": "mp3",
        "opus": "opus",
        "vorbis": "ogg",
        "flac": "flac",
        "wav": "wav",
        "pcm_s16le": "wav",
        "pcm_s24le": "wav",
    }

    try:
        # Run FFprobe to get the audio codec information
        ffprobe_command = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=codec_name",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            input_stream_url,
        ]

        # 5s is usually enough for metadata headers
        codec_info = subprocess.check_output(ffprobe_command, text=True, timeout=5)

        audio_codec = codec_info.strip().split("\n")[0].lower()
        # Return mapped extension or the codec name as fallback
        return CODEC_MAP.get(audio_codec, audio_codec)

    except FileNotFoundError:
        log.error("ffprobe not found! Install FFmpeg to use recording.")
        return None
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        log.debug(f"Could not fetch codec via ffprobe: {e}")
        return None


def record_audio_from_url(
    input_url,
    output_file,
    force_mp3,
    loglevel,
    duration=None,
    station_name=None,
    track_name=None,
):
    """
    Record audio from a URL using FFmpeg.
    """
    log.debug(f"Recording audio from {input_url} to {output_file}")
    try:
        ffmpeg_command = [
            "ffmpeg",
            "-y",  # Overwrite if exists
            "-i",
            input_url,
            "-vn",
            "-stats",
        ]

        if force_mp3:
            ffmpeg_command.extend(["-c:a", "libmp3lame", "-q:a", "2"])
        else:
            ffmpeg_command.extend(["-c:a", "copy"])

        # Add metadata if provided
        if station_name:
            ffmpeg_command.extend(["-metadata", f"service_name={station_name}"])
            ffmpeg_command.extend(["-metadata", f"publisher={station_name}"])
        if track_name:
            ffmpeg_command.extend(["-metadata", f"title={track_name}"])

        ffmpeg_command.append("-loglevel")
        if loglevel == "debug":
            ffmpeg_command.append("info")
        else:
            ffmpeg_command.extend(["error", "-hide_banner"])

        if duration:
            seconds = int(duration) * 60
            ffmpeg_command.extend(["-t", str(seconds)])

        ffmpeg_command.append(output_file)

        # Use stdin=PIPE to allow sending 'q' for graceful termination
        process = subprocess.Popen(
            ffmpeg_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return process

    except FileNotFoundError:
        log.error("FFmpeg not found! Please install it to use recording.")
        return None
    except Exception as ex:
        log.debug(f"FFmpeg startup error: {ex}")
        log.error(f"Error while starting recording: {ex}")
        return None
