import pyttsx3
import speech_recognition as sr
import openai
import os
import atexit
import commands
from threading import Thread, Timer
from datetime import datetime
import keyring
import random


tts = pyttsx3.init()


with open("prompts/actor.txt", 'r') as actor,\
     open("prompts/paths.txt", 'r') as paths:
    actor = actor.read()
    # You need to write paths.txt yourself
    paths = paths.read()


class GPTAnswer:
    """
    Init arg: a string, response from ChatGPT.
    During initialization, the response type is automatically recognized (see the recognize_type method).
    Than the object is parsing and launching and/or voicing
    Multithreading is used to run code and produce speech.
    """
    def __init__(self, text: str):
        self.text = text
        self.type = self.recognize_type()
        if self.type == 2:
            self.do_code()
            self.say()
            self.start()
            # os.remove("temp.bat")

        elif self.type == 1:
            self.code_thread = None
            self.say()
            self.start()

        else:
            self.do_python_code()
            self.say()
            self.start()
    
    def recognize_type(self) -> int:
        """
        Recognizes the type of answer:

        1 - Just an answer

        2 - Bat code

        3 - Python 3.x code (currently 3.10 but I don't know if it affects smth

        Based on the received type, the logic of doing the response will be executed differently.
        """

        if self.text.startswith("#CODE"):
            text = self.text.split("#SOUND")
            self.code = text[0].replace("#CODE", "")
            self.answer = text[1]
            return 2
        
        if self.text.startswith("#PYTHON"):
            text = self.text.split("#SOUND")
            self.python_code = text[0].replace("#PYTHON", "")
            self.python_code = "import os\n" + self.python_code  # I dont know why but gpt often forgets about os module. i have no another idea how to fix that...
            self.answer = text[1]
            return 3
        
        self.answer = self.text
        return 1
    
    def do_code(self):
        """Creates bat code thread"""
        self.write_bat_code_in_file()
        self.code_thread = Timer(1, os.startfile, args=("temp.bat",))
        # print("Создан поток кода...")

    def do_python_code(self):
        """Creates python code thread"""
        self.code_thread = Timer(1, exec, args=(self.python_code,))
        print("Создан поток python кода...")

    def write_bat_code_in_file(self):
        with open("temp.bat", "w") as file:
            file.write(self.code)

    def say(self):
        """Synthesizes speech and creates a speech thread"""
        tts.say(self.answer)
        self.speech_thread = Thread(target=tts.runAndWait)
        print("Создан поток речи...")

    def start(self):
        """
        Starts the speech thread and, if necessary, the code thread.
        """
        self.speech_thread.start()
        print("Запущен поток речи")
        if self.code_thread is not None:
            self.code_thread.start()
            print("Запущен поток кода")

        tts.endLoop()


def get_api_key() -> str:
    """
    Gets OpenAI API-key using keyring
    If key wasnt received from the user - Offers to enter it.
    In this case, the key is adding to the PC memory via keyring.
    """
    key = keyring.get_password("openai", os.getlogin())
    if key is None:
        key = input("Введите ваш openai api ключ: ")
        keyring.set_password("openai", os.getlogin(), key)
        print("Ключ сохранен, вам больше не понадобится его вводить")
        return get_api_key()

    return key


api_key = get_api_key()
openai.api_key = api_key


msgs: list[dict] = [
    {
        "role": "system",
        "content": actor + '\n' + paths
    }
]


completion = openai.ChatCompletion.create(
    model = "gpt-3.5-turbo",
    messages = msgs
)


def end():
    """
    I am going to add here the cleaning of every temp-files
    """
    pass


atexit.register(end)


def ask(text: str) -> GPTAnswer:
    """
    Receives a request from the user, sends it to ChatGPT and returns a GPTAnswer objec (see class GPTAnswer)
    The class is initialized immediately, so it is enough to call this function to reproduce the response.
    Also, logs are writing to `logs/info.txt` in the following format:
    
    {
        time: {
            User's text: ChatGPT's answer
        }
    }

    In the future, the logging system will be significantly improved using json and logging.
    """
    global msgs

    for cmd in commands.cmds.keys():
        if text.lower() in commands.cmds[cmd][0]:
            return GPTAnswer(f"#CODE{cmd}#SOUND{random.choice(commands.cmds[cmd][1])}")
    
    msgs.append({"role": "user", "content": text})

    completion = openai.ChatCompletion.create(
        model = "gpt-3.5-turbo",
        messages = msgs
    )


    # print("Получен ответ от ChatGPT:")
    # print(completion.choices[0].message.content)

    with open("logs/info.txt", "r+", encoding='utf-8') as f:
        log = {str(datetime.now()) : {text : completion.choices[0].message.content.replace("```", "")}}
        f.write(str(log) + '\n')

    return GPTAnswer(completion.choices[0].message.content.replace("```", ""))


# создаем экземпляр класса Recognizer
r = sr.Recognizer()


def main():
    """
    An infinity loop, requsting audio input using mic and sending it to ChatGPT, then the result code is automatically executed and/or the result text is voiced. (See the function `ask`)
    """
    while True:
        # используем PyAudio для получения аудио с микрофона
        with sr.Microphone() as source:
            print("Говорите...")
            audio = r.listen(source)

        # используем Google Web Speech API для распознавания речи
        try:
            print("Принято, распознаётся...")
            text = r.recognize_google(audio, language="ru-RU")
            print(f"Вы сказали {text}, ожидается ответ...")
            ask(text)

        except sr.UnknownValueError:
            continue

        except sr.RequestError as e:
            print(f"Ошибка в работе сервиса распознавания речи: {e}")

        except Exception as e:
            with open("logs/errors.txt", 'r+', encoding='utf-8') as errs:
                current = errs.read()
                new_error = {datetime.now(): e}
                errs.write(current + '\n' + str(new_error))
            print("Неожиданная ошибка. Возможно, вы превысили лимит Запросов (6 запросов в минуту)")


main()
