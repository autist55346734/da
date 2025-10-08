import telebot

TOKEN = ''
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def say_hello(message):
    bot.send_message(message.chat.id, 'Привет! как дела?')

@bot.message_handler(commands=['help'])
def say_hello(message):
    bot.send_message(message.chat.id, 'Чем могу тебе помочь?')


@bot.message_handler(content_types=['text'])
def handel_massage(message):
    txt = (
        "Я - разговорный бот. Нужен для того что "
        "чем-то вам помочь"
    )
    bot.send_message(message.chat.id, txt)


print('ok')
bot.polling(
    none_stop=True,
    interval=1
)
