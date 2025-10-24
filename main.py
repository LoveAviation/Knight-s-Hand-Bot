import os
import telebot
from telebot import types
from io import BytesIO
from PIL import Image

TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN не задан. Установите переменную окружения.")

bot = telebot.TeleBot(TOKEN)

canvas_command = "Холст сюда!"

menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
canvas = types.KeyboardButton(canvas_command)
menu.add(canvas)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id,"Привет! \nЯ пока что могу только подносить холст в чат группы, но надеюсь смогу большее!", reply_markup=menu)

@bot.message_handler(content_types=['text'])
def text_messages(message):
    if message.text == canvas_command:
        # Создаём белое изображение (например, 1200x800 пикселей)
        img = Image.new("RGB", (1200, 800), color="white")

        # Сохраняем в память (чтобы не писать на диск)
        bio = BytesIO()
        bio.name = 'canvas.jpg'
        img.save(bio, 'JPEG')
        bio.seek(0)

        # Отправляем в чат
        bot.send_photo(message.chat.id, bio, caption="Ваш чистый холст, сэр!")

        bio.close()
        del img
bot.infinity_polling()