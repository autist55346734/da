import telebot
import random

TOKEN = ""
bot = telebot.TeleBot(TOKEN)
users_info = {}

class MyException(Exception):
    pass

@bot.message_handler(commands=["start"])
def say_hello(message):
    txt = (
        "Я загадал число от 1 до 100. "
        "Угадай это число за 7 попыток. "
        "Чтобы начать игру напиши слово - начать"
    )
    bot.send_message(message.chat.id, txt)

@bot.message_handler(content_types = ["text"])
def handle_message(message):
    user_id = message.chat.id
    txt = message.text.strip().lower()
    if txt == "начать":
        n = random.randint(1, 100)
        users_info[user_id] = {
            "number": n,
            "tries": 0
        }
        bot.send_message(user_id, "Я загадал, начинай!")
    else:
        try:
            n = int(txt)
            if user_id not in users_info:
                raise MyException("Вы ещё не начали игру")
            if not 1 <= n <= 100:
                raise MyException ("Введите число из диапазона от 1 до 100")
            users_info[user_id]["tries"] += 1
            x = users_info[user_id]["number"]
            if n == x:
                k = users_info[user_id]["tries"]
                bot.send_message(user_id, f"Ура, вы угадали! Кол-во попыток: {k}")
                del users_info[user_id]
            elif n > x:
                bot.send_message(user_id, f"Загаданное число меньше")
            else:
                bot.send_message(user_id, f"Загаданное число больше")
        except ValueError:
            bot.send_message(user_id, "Я только принимаю слово - начать")
        except MyException as me:
            bot.send.messsage(user_id, me)

print("всё норм")
bot.polling(
    none_stop=True,
    interval=1
)
