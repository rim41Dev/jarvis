import pyttsx3
from threading import Thread
# from typing import NewType (⊙_⊙)


class Status:
    def __init__(self, err: Exception=None) -> None:
        self.value = err if err is not None else "OK"


class SecondGPTChat: ... # (⊙_⊙) х2


def say(text: str) -> Status:
    try:
        tts = pyttsx3.init()
        tts.say(text)
        speech_thread = Thread(target=tts.runAndWait)
        speech_thread.start()
        tts.endLoop()
    except Exception as e:
        return Status(err = e)
    return Status()
