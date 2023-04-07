import speech_recognition as sr

from utils import get_openai_key
from prompt import speech_to_prompt

def voice_to_prompt():
    r = sr.Recognizer()
    r.pause_threshold = 1

    with sr.Microphone() as source:
        print("Start recording...")
        audio = r.listen(source)
    
    try:
        speech = r.recognize_whisper_api(audio, api_key=get_openai_key())
        print("Detected speech: ", speech)
    except sr.RequestError as e:
        print(f"Could not request results from Whisper API: {e}")

    speech = speech.lower()
    if "verbose" in speech:
        speech = speech.replace("verbose", "").strip()
        print("Verbose mode: ", speech)
        return speech

    try:
        prompt = speech_to_prompt(speech)
        print("Generated prompt: ", prompt)
    except Exception as e:
        print(f"Could not generate prompt: {e}")
        prompt = speech
    
    return prompt