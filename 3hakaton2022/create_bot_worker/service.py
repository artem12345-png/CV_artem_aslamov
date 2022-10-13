from uuid import uuid4
from telegram.client import Telegram
import threading
import time

ls = ["metricakjdnchjscdfenvjfnjnfn", 'fgfjgnjfvnjnkjndklacacffsjnvfefg']


def parse_token(text):
    print(text)
    return text[text.find('API:\n'):].split('\n')[1]


def parse_link_on_bot(text):
    print(text)
    return text[text.find('t.me/'):].split('. ')[0]


def parse_message(telegram):
    get_chat_history = telegram.get_chat_history(
        chat_id=d["chat_id"],
    )

    get_chat_history.wait()
    print("S"*100)
    print(get_chat_history.update)
    print("S"*100)
    last_message = get_chat_history.update.get('messages')[0].get("content").get("text").get("text")
    return last_message


def command_new_bot(telegram):
    """
    создаем бота
    """

    print("get chats")
    # get_chats = telegram.get_chats()
    # get_chats.wait()
    print("send /newbot")
    result = telegram.send_message(
        chat_id=d["chat_id"],
        text='/newbot'
    )
    result.wait()
    time.sleep(2)
    print("get last message in command_new_bot")
    last_message = parse_message(telegram)

    if "Sorry, too many attempts. Please try again in" in last_message:
        seconds = last_message.split(' second')[0].split()[-1]
        if int(seconds) < 300:
            time.sleep(int(seconds))
            return 4
        elif int(seconds) > 300:
            return False
    else:
        return True


def create_username(telegram, nickname, theme):
    result = telegram.send_message(
        chat_id=d["chat_id"],
        text=f'{nickname}_{theme}',
    )
    result.wait()
    time.sleep(2)


def create_bot_id(telegram, telegram_id, theme):
    result = telegram.send_message(
        chat_id=d["chat_id"],
        text=f'{telegram_id}_{theme}_bot'
    )
    result.wait()
    time.sleep(2)

    last_message = parse_message(telegram)
    if last_message in "Sorry, this username is already taken. Please try something different.":
        return 3
    elif last_message in "Sorry, this username is invalid.":
        return 4

    return 0


messages = []


def create_new_bot(telegram, theme, telegram_id, nickname):
    while True:
        print("print command /newbot")
        r = command_new_bot(telegram)
        if r is False:  # пишем бот фазеру команду на создание бота
            print("return 1")
            return 1
        elif r == 4:
            print("continue")
            continue
        print("create username")

        create_username(telegram, nickname + str(uuid4())[:4], theme)  # пишем бот фазеру название бота
        print("create bot_id")
        res_bot_id = create_bot_id(telegram, telegram_id + str(uuid4())[:4], theme)  # пишем бот фазеру id бота

        while True:
            if res_bot_id == 3:
                print("пишем чуваку что такой айдишник занят")
                continue
            elif res_bot_id == 4:
                print("пишем чуваку что такой айдишник не корректный")
                continue
            elif res_bot_id == 0:
                print("parsing last message")
                messages.append(tuple((parse_token(parse_message(telegram)),
                                   parse_link_on_bot(
                                       parse_message(telegram)))))  # забираем последние сообщение вместе с токеном
                break
        print(messages)
        time.sleep(1)

        return 2


def thread_function(telegram):
    get_chats = telegram.get_chats()
    get_chats.wait()
    theme, telegram_id, nickname = 'russian', 'aalamovvvvv', 'aaalvvv'
    while True:
        # listen_rabit
        print("create new bot")
        res = create_new_bot(telegram, theme, telegram_id, nickname)
        if res == 1:
            return False
        else:
            break


d = {
    "api_id": 12862801,
    "api_hash": "8fbd9e37d17ea8c22b720379bd634665",
    "phone": "+79934815229",
    "chat_id": 93372553,
    "message": "/newbot"
}


def telega(tg):
    tg.idle(stop_signals=tuple())


sessions = ["denis1", "denis", "tanya", "valya", "vanya", "artem", "artem1", "artem2"]
data_d = {
    "denis": {
        "api_id": 15346335,
        "api_hash": "ab975bf2de0075626d503de43cd1ecb6",
        "phone": "+79955721126"
    },
    "tanya": {
        "api_id": 11378102,
        "api_hash": "f4e2c84737de572096f37a9455f9e4f5",
        "phone": "+79955760125"
    },
    "valya": {
        "api_id": 10274919,
        "api_hash": "898c2df940931bfa96ddaff69133053b",
        "phone": "+79955680722"
    },
    "vanya": {
        "api_id": 12862801,
        "api_hash": "8fbd9e37d17ea8c22b720379bd634665",
        "phone": "+79934815229"
    },
    "artem": {
        "api_id": 19511614,
        "api_hash": "3288899181fa6969c14754c5c4334aac",
        "phone": "+79955703002"
    },
    "artem1": {
        "api_id": 10523561,
        "api_hash": "3f8184fa0fb571ad2ad2a1613f40e0c6",
        "phone": "+79529023452"
    },
    "artem2": {
        "api_id": 16829172,
        "api_hash": "2b7fa8de41e1d0d03d76f5b3078a980c",
        "phone": "+79955682071"
    },
    "denis1": {
        "api_id": 9120524,
        "api_hash": "11a018022698264afcdb9d7d9176231c",
        "phone": "+79955732611"
    },
}


def main():
    for session in sessions:
        print(session + " manin")
        tg = Telegram(
            api_id=data_d[session]["api_id"],
            api_hash=data_d[session]["api_hash"],
            phone=data_d[session]["phone"],
            database_encryption_key='changeme1234',
            files_directory=f'./{session}'
        )
        print("loging")
        tg.login()
        x = threading.Thread(target=telega, args=(tg,))
        x.start()
        res = thread_function(tg)

        if res is False:
            tg.stop()
            del x
            continue
        else:
            print(res)
            break


main()
