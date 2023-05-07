import keyring
from os import getlogin


def get_current() -> (str | None):
    """Возвращает первые и последние символы API ключа, если он есть"""

    key = keyring.get_password("openai", getlogin())
    if key is not None:
        return "..........".join([key[:7], key[len(key) - 6:]])
    
    return key


def set_new():
    """Устанавливает новый API ключ"""

    print("Текущий ключ:\n" + (get_current() if get_current() is not None else "Отсутствует"))
    print("Вы уверены, что хотите изменить ключ? Это действие нельзя будет отменить")
    confirm = input("Y/n")
    
    if confirm.lower() in ("y", "да", "yes", "д", "ok", "ок"):
        new_key = input("Введите новый API ключ: ")
        keyring.set_password("openai", getlogin(), new_key)
        print("Ключ успешно изменён")

    else:
        # А что сюда сделать то можно ¯ \ _ (ツ) _ / ¯
        pass


if __name__ == "__main__":
    set_new()