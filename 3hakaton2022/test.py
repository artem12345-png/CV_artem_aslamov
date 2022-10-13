from telegram.client import Telegram
import threading
import time

print('xuy')

d = {
    "api_id": 10523561,
    "api_hash": "3f8184fa0fb571ad2ad2a1613f40e0c6",
    "phone": "+79529023452",
    "chat_id": 93372553,
    "message": "/newbot"

}

ls = ["metricakjdnchjscdfenvjfnjnfn", 'fgfjgnjfvnjnkjndklacacffsjnvfefg']
messages = []


def create_new_bot():

    for item in ls:

        """
        создаем бота
        """
        result = tg.send_message(
            chat_id=d["chat_id"],
            text=d["message"]
        )
        result.wait()
        get_chat_history = tg.get_chat_history(
            chat_id=d["chat_id"]
        )
        get_chat_history.wait()
        print("--" * 100)
        print(get_chat_history.update)
        last_message = get_chat_history.update.get('messages')[-1].get("content").get("text").get("text")
        if "Sorry, too many attempts. Please try again in" in last_message:
            seconds = last_message.split(' second')[0].split()[-1]
            time.sleep(int(seconds))
            return False
        else:
            result = tg.send_message(
                chat_id=d["chat_id"],
                text=item
            )
            result = tg.send_message(
                chat_id=d["chat_id"],
                text=item + '_bot'
            )

            get_chat_history = tg.get_chat_history(
                chat_id=d["chat_id"]
            )
            get_chat_history.wait()
            print("--" * 100)
            print(get_chat_history.update)
            last_message = get_chat_history.update.get('messages')[-1].get("content").get("text").get("text")

            if last_message in "Sorry, this username is already taken. Please try something different.":
                result = tg.send_message(
                    chat_id=d["chat_id"],
                    text="Такое username уже занят"
                )
            elif last_message in "Sorry, this username is invalid.":
                result = tg.send_message(
                    chat_id=d["chat_id"],
                    text="неккоректный username"
                )
            get_chat_history = tg.get_chat_history(
                chat_id=d["chat_id"]
            )
            time.sleep(20)
            get_chat_history.wait()
            print(get_chat_history.update)
            last_message = get_chat_history.update.get('messages')[-1].get("content").get("text").get("text")
            print(last_message)
            messages.append(last_message)
            print(messages)


def thread_function(tg):
    while True:
        # listen_rabit
        res = create_new_bot()
        if res is False:
            continue

print(d)
# parser = argparse.ArgumentParser()
# parser.add_argument('19895287', help='API id')  # https://my.telegram.org/apps
# parser.add_argument('753576228824b61625d5d5faa1e87731', help='API hash')
# parser.add_argument('79149474527', help='Phone')
# parser.add_argument('93372553', help='Chat id', type=int)
# parser.add_argument('hi', help='Message text')
#
# args = parser.parse_args()


tg = Telegram(
    api_id=d["api_id"],
    api_hash=d["api_hash"],
    phone=d["phone"],
    database_encryption_key='changeme1234',
  #  files_directory='./tanya'
)

# you must call login method before others
tg.login()
x = threading.Thread(target=thread_function, args=(tg,))
x.start()
    # x.join()

# tg.add_message_handler(new_message_handler)
tg.idle()
# if this is the first run, library needs to preload all chats
# otherwise the message will not be sent
# get_chats = tg.get_chats()
#
# # `tdlib` is asynchronous, so `python-telegram` always returns you an `AsyncResult` object.
# # You can wait for a result with the blocking `wait` method.
# get_chats.wait()
#
# if get_chats.error:
#     print(f'get chats error: {get_chats.error_info}')
# else:
#     print(f'chats: {get_chats.update}')
# print('_'*100)
# result = tg.send_message(
#     chat_id=d["chat_id"],
#     text=d["message"],
# )
#
# result.wait()
# # result.parse_update()
# get_chats = tg.get_chats()
#
# # `tdlib` is asynchronous, so `python-telegram` always returns you an `AsyncResult` object.
# # You can wait for a result with the blocking `wait` method.
# get_chats.wait()
# if result.error:
#     print(f'send message error: {result.error_info}')
# else:
#     print(f'message has been sent: {result.update}')
#
# res1 = tg.send_message(
#     chat_id=d["chat_id"],
#     text="den",
# )
# res1.wait()
# get_chats = tg.get_chats()
#
# # `tdlib` is asynchronous, so `python-telegram` always returns you an `AsyncResult` object.
# # You can wait for a result with the blocking `wait` method.
# get_chats.wait()
# # res1.parse_update()
# res1.wait()
#
# res2 = tg.send_message(
#     chat_id=d["chat_id"],
#     text="soldatov_den_liter_bot",
# )
# res2.wait()
# # res2.parse_update()
# res2.wait()
#
# get_chats = tg.get_chats()
#
# # `tdlib` is asynchronous, so `python-telegram` always returns you an `AsyncResult` object.
# # You can wait for a result with the blocking `wait` method.
# get_chats.wait()
#
# get_chat_history = tg.get_chat_history(
#     chat_id=d["chat_id"],
# )
# get_chat_history.wait()
#
# print("--"*1000)
# print(get_chat_history.update)
# print("--"*1000)
# last_message = get_chat_history.update.get('messages')[-1].get("content").get("text").get("text")
# print(last_message)
# tg.stop()
