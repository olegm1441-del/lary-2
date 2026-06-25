import io
import wave


class AudioPayloadError(Exception):
    pass


def audio_to_pcm16_16khz(audio: bytes, content_type: str | None) -> bytes:
    normalized = (content_type or "").split(";")[0].strip().lower()
    if normalized in {"audio/wav", "audio/x-wav"}:
        return _wav_to_pcm(audio)
    if normalized == "audio/x-pcm":
        return audio
    raise AudioPayloadError("unsupported_audio_format")


def _wav_to_pcm(audio: bytes) -> bytes:
    try:
        with wave.open(io.BytesIO(audio), "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            frame_rate = wav_file.getframerate()
            frames = wav_file.readframes(wav_file.getnframes())
    except wave.Error as exc:
        raise AudioPayloadError("unsupported_audio_format") from exc

    if channels != 1 or sample_width != 2 or frame_rate != 16000:
        raise AudioPayloadError("unsupported_audio_format")
    return frames
