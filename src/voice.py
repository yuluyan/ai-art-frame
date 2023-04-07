import speech_recognition as sr

from utils import get_openai_key
from prompt import speech_to_prompt

def voice_to_prompt(record_start_callback=None, record_end_callback=None, verbose_callback=None):
    r = sr.Recognizer()
    r.pause_threshold = 1

    with sr.Microphone() as source:
        print("Start recording...")
        if record_start_callback:
            record_start_callback()
        r.adjust_for_ambient_noise(source)
        audio = r.listen(source)

    if record_end_callback:
        record_end_callback()

    def _verbose_callback(msg):
        if verbose_callback:
            verbose_callback(msg)
        print(msg)

    try:
        speech = r.recognize_whisper_api(audio, api_key=get_openai_key())
        _verbose_callback(f"Detected speech: {speech}")
        
    except sr.RequestError as e:
        _verbose_callback(f"Could not request results from Whisper API: {e}")

    speech = speech.lower()
    if "verbose" in speech:
        speech = speech.replace("verbose", "").strip()
        _verbose_callback(f"Verbose mode: {speech}")
        return speech

    try:
        prompt = speech_to_prompt(speech)
        _verbose_callback(f"Generated prompt: {prompt}")
    except Exception as e:
        _verbose_callback(f"Could not generate prompt: {e}")
        prompt = speech
    
    return prompt