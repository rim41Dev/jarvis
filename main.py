import pyttsx3
import speech_recognition as sr
import openai
import os
import atexit
import commands
from threading import Thread, Timer
from datetime import datetime
import keyring


tts = pyttsx3.init()


with open("prompts/actor.txt", 'r') as actor,\
     open("prompts/paths.txt", 'r') as paths:
    actor = actor.read()
    paths = paths.read()


class GPTAnswer:
    """
    Класс, принимающий при инициализации аргументом строку - ответ от ChatGPT.
    При инициализации автоматически распознается тип ответа (см. метод recognize_type), ответ парсится и запускается и/или озвучивается
    Для запуска кода и произведения речи используется многопоточность.
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
        Распознает тип ответа от ChatGPT:

        1 - Ответ

        2 - Код для выполнения bat

        3 - код python 3.x

        На основании полученного типа будет по разному выполнятся логика воспроизведения ответа.
        """

        if self.text.startswith("#CODE"):
            text = self.text.split("#SOUND")
            self.code = text[0].replace("#CODE", "")
            self.answer = text[1]
            return 2
        
        if self.text.startswith("#PYTHON"):
            text = self.text.split("#SOUND")
            self.python_code = text[0].replace("#PYTHON", "")
            self.answer = text[1]
            return 3
        
        self.answer = self.text
        return 1
    
    def do_code(self):
        """Создаёт поток bat кода"""
        self.write_bat_code_in_file()
        self.code_thread = Timer(1, os.startfile, args=("temp.bat",))
        # print("Создан поток кода...")

    def do_python_code(self):
        """Создает поток python кода"""
        self.code_thread = Timer(1, exec, args=(self.python_code,))
        print("Создан поток python кода...")

    def write_bat_code_in_file(self):
        with open("temp.bat", "w") as file:
            file.write(self.code)

    def say(self):
        """Синтезирует речь и создаёт поток речи"""
        tts.say(self.answer)
        self.speech_thread = Thread(target=tts.runAndWait)
        print("Создан поток речи...")

    def start(self):
        """
        Запускает поток речи и при необходимости поток кода.
        """
        self.speech_thread.start()
        print("Запущен поток речи")
        if self.code_thread is not None:
            self.code_thread.start()
            print("Запущен поток кода")

        tts.endLoop()


def get_api_key() -> str:
    """
    При помощи keyring извлекается API-ключ OpenAI.
    Если ключ не был введен - предлагается ввести его.
    В таком случае ключ добавляется в память ПК через keyring.
    """
    key = keyring.get_password("openai", os.getlogin())
    if key is None:
        key = input("Введите ваш openai api ключ: ")
        keyring.set_password("openai", os.getlogin(), key)
        print("Ключ сохранен, вам больше не понадобится его вводить")
        return get_api_key()

    return key


# api_key = "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"
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
    Рассчитывается добавить сюда чистку всех временных файлов, созданных в процессе работы.
    """
    pass


atexit.register(end)


def ask(text: str) -> GPTAnswer:
    """
    Получает запрос от пользователя, отправляет в ChatGPT и возвращает объект класса GPTAnswer (см. class GPTAnswer)
    Класс сразу инициализируется, поэтому для воспроизведения ответа достаточно вызвать эту функцию.
    Также ведется запись логов в файл по пути logs/info.txt в формате
    
    {
        время: {
            Текст запроса: Ответ от ChatGPT
        }
    }

    В будущем система логов будет существенно доработана с использованием json и logging.
    """
    global msgs

    for cmd in commands.cmds.keys():
        if text.lower() in commands.cmds[cmd]:
            return GPTAnswer(f"#CODE{cmd}")
    
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
    Бесконечный цикл, запрашивающий аудио ввод через микрофон и отправляющий его в ChatGPT, затем автоматически выполняется код результата и/или озвучивается текст результата. Подробнее см. функцию ask.
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

        except:
            print("Неожиданная ошибка. Возможно, вы превысили лимит Запросов (6 запросов в минуту)")


main()
