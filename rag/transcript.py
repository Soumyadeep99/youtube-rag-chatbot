import re
import os
import tempfile

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound


def extract_video_id(url: str) -> str | None:
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
        r"(?:youtu\.be\/)([0-9A-Za-z_-]{11})",
        r"(?:embed\/)([0-9A-Za-z_-]{11})"
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def get_video_title(video_id: str) -> str:
    try:
        import yt_dlp
        url = f"https://www.youtube.com/watch?v={video_id}"
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "no_warnings": True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get("title", "")
            if title:
                return title[:40] + ("..." if len(title) > 40 else "")
    except Exception as e:
        print(f"[Title Fetch Error] {e}")
    return f"Video {video_id[:8]}"


def get_transcript(video_id: str) -> str | None:
    # Attempt 1: YouTube Transcript API
    try:
        transcript_list = YouTubeTranscriptApi().fetch(video_id)
        text = " ".join(entry.text for entry in transcript_list)
        if text.strip():
            return text
    except (TranscriptsDisabled, NoTranscriptFound):
        print(f"[Transcript] No captions for {video_id}. Falling back to Whisper...")
    except Exception as e:
        print(f"[Transcript API Error] {e}. Falling back to Whisper...")

    # Attempt 2: Whisper fallback
    return _transcribe_with_whisper(video_id)


def _transcribe_with_whisper(video_id: str) -> str | None:
    try:
        import yt_dlp

        url = f"https://www.youtube.com/watch?v={video_id}"

        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = os.path.join(tmpdir, "audio")

            format_attempts = [
                "bestaudio[ext=m4a]",
                "bestaudio[ext=webm]",
                "bestaudio",
                "worstaudio",
                "best",
            ]

            downloaded = False
            for fmt in format_attempts:
                try:
                    ydl_opts = {
                        "format": fmt,
                        "outtmpl": audio_path,
                        "quiet": True,
                        "no_warnings": True,
                        "postprocessors": [{
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": "mp3",
                            "preferredquality": "64"
                        }]
                    }
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([url])
                    downloaded = True
                    print(f"[yt-dlp] Downloaded with format: {fmt}")
                    break
                except Exception as e:
                    print(f"[yt-dlp] Format '{fmt}' failed: {e}")
                    continue

            if not downloaded:
                print("[Whisper] All format attempts failed.")
                return None

            # Find downloaded file
            final_audio = None
            for ext in ["mp3", "m4a", "webm", "opus", "ogg"]:
                candidate = f"{audio_path}.{ext}"
                if os.path.exists(candidate):
                    final_audio = candidate
                    break

            if not final_audio:
                print("[Whisper] Audio file not found after download.")
                return None

            # Try Groq first (fast), fallback to local Whisper
            groq_key = os.getenv("GROQ_API_KEY")
            if groq_key:
                result = _groq_transcribe(final_audio, groq_key)
                if result:
                    return result

            return _local_whisper_transcribe(final_audio)

    except Exception as e:
        print(f"[Whisper Error] {e}")
        return None


def _groq_transcribe(audio_path: str, api_key: str) -> str | None:
    try:
        from groq import Groq
        print("[Groq Whisper] Transcribing via Groq API...")
        client = Groq(api_key=api_key)
        with open(audio_path, "rb") as f:
            transcription = client.audio.transcriptions.create(
                file=f,
                model="whisper-large-v3-turbo"
            )
        return transcription.text
    except Exception as e:
        print(f"[Groq Transcription Error] {e}. Falling back to local Whisper...")
        return None


def _local_whisper_transcribe(audio_path: str) -> str | None:
    try:
        import whisper
        print("[Local Whisper] Transcribing on CPU...")
        model = whisper.load_model("tiny")
        result = model.transcribe(audio_path)
        text = result.get("text", "").strip()
        return text if text else None
    except Exception as e:
        print(f"[Local Whisper Error] {e}")
        return None