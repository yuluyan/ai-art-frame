import queue
import uuid
import threading
import time
import typing

import speech_recognition as sr

from utils import get_openai_key


def standard_recognize(
    microphone: sr.Microphone, 
    recognizer: sr.Recognizer, 
    timeout: typing.Optional[int], 
    start_callback: typing.Optional[typing.Callable[[], typing.NoReturn]] = None, 
    end_callback: typing.Optional[typing.Callable[[], typing.NoReturn]] = None,
    *,
    to_lower: bool = True,
) -> typing.Optional[str]:
    with microphone as source:
        recognizer.adjust_for_ambient_noise(source)
        if start_callback:
            start_callback()
        audio = recognizer.listen(source, timeout=timeout)

    if end_callback:
        end_callback()

    try:
        api_key = get_openai_key()
        speech = recognizer.recognize_whisper_api(audio, api_key=api_key)
    except sr.RequestError as e:
        print(f"Could not request results from Whisper API: {e}")
        speech = None

    if speech and to_lower:
        speech = speech.lower()

    return speech


class VoiceManager:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()

        self.recognizer.pause_threshold = 1
        self.microphone_loop_duration = 5
        self.microphone_loop_pause = 0.1

        self.trigger_models = {}
        self.phrase_mapping = {}

        self.running = False
        self.modal = False
        self.command_queue = queue.Queue()
        self.microphone_lock = threading.Lock()
        
        self.disable_background_listening = False

    def register_trigger_phrases(
        self, 
        phrases: typing.List[str], 
        callback: typing.Callable[..., typing.NoReturn], 
        wait_start_callback: typing.Optional[typing.Callable[..., typing.NoReturn]] = None, 
        wait_end_callback: typing.Optional[typing.Callable[..., typing.NoReturn]] = None, 
        priority: int = 0, 
        modal: bool = False
    ):
        phrases = [p.lower().strip(",.!?:;") for p in phrases]
        phrase_id = str(uuid.uuid4())

        self.trigger_models[phrase_id] = {
            "phrases": phrases,
            "priority": priority,
            "modal": modal, 
            "callback": callback,
            "wait_start_callback": wait_start_callback,
            "wait_end_callback": wait_end_callback,
        }

        for p in phrases:
            self.phrase_mapping[p.lower()] = phrase_id

    def _listen_for_commands(self):
        while self.running and not self.disable_background_listening:
            if not self.modal:
                try:
                    with self.microphone_lock:
                        with self.microphone as source:
                            self.recognizer.adjust_for_ambient_noise(source)
                            audio = self.recognizer.listen(source, timeout=self.microphone_loop_duration)

                    speech = self.recognizer.recognize_whisper_api(audio, api_key=get_openai_key())
                    speech = speech.lower()

                    matched_id = []
                    for trigger_phrase, phrase_id in self.phrase_mapping.items():
                        if trigger_phrase in speech:
                            matched_id.append(phrase_id)

                    if matched_id:
                        highest_priority = max([self.trigger_models[id]["priority"] for id in matched_id])
                        for id in matched_id:
                            if self.trigger_models[id]["priority"] == highest_priority:
                                self.command_queue.put((id, speech))
                                if self.trigger_models[id]["wait_start_callback"]:
                                    self.trigger_models[id]["wait_start_callback"]()

                except sr.RequestError as e:
                    print(f"Could not request results from Whisper API: {e}")
                    
                except (sr.UnknownValueError, sr.WaitTimeoutError):
                    pass

            time.sleep(self.microphone_loop_pause)

    def _process_commands(self):
        while self.running:
            while not self.command_queue.empty():
                id, speech = self.command_queue.get()
                modal = self.trigger_models[id]["modal"]
                callback = self.trigger_models[id]["callback"]
                wait_end_callback = self.trigger_models[id]["wait_end_callback"]

                if modal:
                    self.modal = True
                    with self.microphone_lock:
                        if wait_end_callback:
                            wait_end_callback()
                        callback(speech, self.microphone, self.recognizer)
                        self.command_queue.queue.clear()  # Clear the queue for modal commands
                    self.modal = False
                else:
                    if wait_end_callback:
                        wait_end_callback()
                    callback(speech)
            time.sleep(self.microphone_loop_pause)

    def start(self):
        self.running = True

        self.listen_thread = threading.Thread(target=self._listen_for_commands)
        self.process_thread = threading.Thread(target=self._process_commands)
        self.listen_thread.daemon = True
        self.process_thread.daemon = True

        self.listen_thread.start()
        self.process_thread.start()

    def stop(self):
        self.running = False
        self.modal = False

        self.listen_thread.join()
        self.process_thread.join()

    def trigger(self, phrase):
        if phrase in self.phrase_mapping:
            id = self.phrase_mapping[phrase]
            speech = phrase
            self.command_queue.put((id, speech))
            if self.trigger_models[id]["wait_start_callback"]:
                self.trigger_models[id]["wait_start_callback"]()
        else:
            raise ValueError(f"Phrase {phrase} not registered")
