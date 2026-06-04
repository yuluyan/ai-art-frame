import logging
import queue
import uuid
import threading
import time
import typing

import requests
import speech_recognition as sr

from utils import get_openai_key

logger = logging.getLogger(__name__)

OPENAI_TRANSCRIBE_URL = "https://api.openai.com/v1/audio/transcriptions"
TRANSCRIBE_MODEL = "whisper-1"


def transcribe_audio(audio_data, model: str = TRANSCRIBE_MODEL) -> typing.Optional[str]:
    """Transcribe AudioData via OpenAI's audio transcription API (direct HTTP).

    Avoids SpeechRecognition's recognizer methods, whose names have churned
    across releases (e.g. recognize_whisper_api -> recognize_openai, which also
    needs the extra `openai` package), and needs nothing beyond requests.
    """
    wav = audio_data.get_wav_data()
    headers = {"Authorization": f"Bearer {get_openai_key()}"}
    files = {"file": ("audio.wav", wav, "audio/wav")}
    data = {"model": model}
    response = requests.post(OPENAI_TRANSCRIBE_URL, headers=headers, files=files, data=data, timeout=60)
    if response.status_code != 200:
        raise RuntimeError(f"OpenAI transcription {response.status_code}: {response.text.strip()}")
    return response.json().get("text")


def standard_recognize(
    microphone: sr.Microphone,
    recognizer: sr.Recognizer,
    timeout: typing.Optional[int],
    start_callback: typing.Optional[typing.Callable[[], None]] = None,
    end_callback: typing.Optional[typing.Callable[[], None]] = None,
    *,
    to_lower: bool = True,
) -> typing.Optional[str]:
    try:
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source)
            if start_callback:
                start_callback()
            audio = recognizer.listen(source, timeout=timeout)
    except sr.WaitTimeoutError:
        logger.info("Listening timed out: no speech detected.")
        if end_callback:
            end_callback()
        return None
    except OSError as e:
        logger.warning(f"Microphone error: {e}")
        if end_callback:
            end_callback()
        return None

    if end_callback:
        end_callback()

    try:
        speech = transcribe_audio(audio)
    except Exception as e:
        logger.warning(f"Transcription failed: {e}")
        speech = None

    if speech and to_lower:
        speech = speech.lower()

    return speech


class VoiceManager:
    """Button-triggered, modal voice capture.

    A trigger (e.g. the NEW button calling ``trigger("generate")``) enqueues a
    command that the worker thread runs modally: it owns the mic, invokes the
    registered callback (which listens, transcribes and generates), then frees
    the mic. Continuous background listening was removed — it was permanently
    disabled and unused.
    """

    def __init__(self, device_index=None):
        self.recognizer = sr.Recognizer()

        # The default ALSA/PortAudio input device may be an output-only card
        # (e.g. HDMI), which makes sr.Microphone() raise on init. Pick a device
        # that can actually capture, and keep the app alive if none exists.
        self.microphone = None
        self.available = False
        try:
            index = device_index if device_index is not None else self._find_input_device()
            if index is None:
                raise RuntimeError("no input-capable audio device found")
            self.microphone = sr.Microphone(device_index=index)
            self.available = True
        except Exception as e:
            logger.warning(f"Voice control disabled (no usable microphone): {e}")

        self.recognizer.pause_threshold = 1
        self.loop_pause = 0.1

        self.trigger_models = {}
        self.phrase_mapping = {}

        self.running = False
        self.modal = False
        self.command_queue = queue.Queue()
        self.microphone_lock = threading.Lock()
        self.process_thread = None

    @staticmethod
    def _find_input_device():
        """PyAudio index of a usable input device, or None.

        Prefers the system default input, then falls back to the first device
        that reports input channels (e.g. a USB mic that isn't the default)."""
        pa = sr.Microphone.get_pyaudio().PyAudio()
        try:
            try:
                info = pa.get_default_input_device_info()
                if info and info.get("maxInputChannels", 0) > 0:
                    return info["index"]
            except Exception:
                pass
            for i in range(pa.get_device_count()):
                info = pa.get_device_info_by_index(i)
                if info.get("maxInputChannels", 0) > 0:
                    return i
        finally:
            pa.terminate()
        return None

    def register_trigger_phrases(
        self,
        phrases: typing.List[str],
        callback: typing.Callable[..., None],
        wait_start_callback: typing.Optional[typing.Callable[..., None]] = None,
        wait_end_callback: typing.Optional[typing.Callable[..., None]] = None,
        modal: bool = False,
    ):
        phrases = [p.lower().strip(",.!?:;") for p in phrases]
        phrase_id = str(uuid.uuid4())

        self.trigger_models[phrase_id] = {
            "modal": modal,
            "callback": callback,
            "wait_start_callback": wait_start_callback,
            "wait_end_callback": wait_end_callback,
        }

        for p in phrases:
            self.phrase_mapping[p.lower()] = phrase_id

    def _process_commands(self):
        while self.running:
            while not self.command_queue.empty():
                cmd_id, speech = self.command_queue.get()
                model = self.trigger_models.get(cmd_id)
                if model is None:
                    continue
                callback = model["callback"]
                wait_end_callback = model["wait_end_callback"]

                if model["modal"]:
                    # Own the mic for the whole modal interaction; always clear
                    # the modal flag even if the callback raises, or voice would
                    # be stuck "busy" forever.
                    self.modal = True
                    try:
                        with self.microphone_lock:
                            if wait_end_callback:
                                wait_end_callback()
                            callback(speech, self.microphone, self.recognizer)
                            self.command_queue.queue.clear()
                    except Exception as e:
                        logger.exception(f"Voice command failed: {e}")
                    finally:
                        self.modal = False
                else:
                    try:
                        if wait_end_callback:
                            wait_end_callback()
                        callback(speech)
                    except Exception as e:
                        logger.exception(f"Voice command failed: {e}")
            time.sleep(self.loop_pause)

    def start(self):
        if not self.available:
            logger.info("Voice control unavailable; worker not started.")
            return
        self.running = True
        self.process_thread = threading.Thread(target=self._process_commands, daemon=True)
        self.process_thread.start()

    def stop(self):
        if not self.running:
            return
        self.running = False
        self.modal = False
        # Daemon thread; bound the wait so shutdown/restart can't hang behind an
        # in-flight generation (which can take minutes).
        if self.process_thread is not None:
            self.process_thread.join(timeout=2)

    def trigger(self, phrase):
        if not self.available:
            return
        if phrase in self.phrase_mapping:
            cmd_id = self.phrase_mapping[phrase]
            self.command_queue.put((cmd_id, phrase))
            wait_start_callback = self.trigger_models[cmd_id]["wait_start_callback"]
            if wait_start_callback:
                wait_start_callback()
        else:
            raise ValueError(f"Phrase {phrase} not registered")
