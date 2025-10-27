import os
import threading
import time
import requests
from io import BytesIO
from PIL import Image
from flask import Flask
import telebot
from telebot import types

TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN не задан. Установите переменную окружения.")

bot = telebot.TeleBot(TOKEN)

# ===== 2. Flask сервер =====
app = Flask(__name__)

@app.route('/')
def home():
    return "I'm alive!"  # Render проверяет, жив ли сервер

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


# ===== 4. Keep-alive (самопинг) =====
def keep_alive():
    """
    Функция каждые 10 минут пингует сам Render-сервис,
    чтобы сервер не "уснул".
    """
    url = "https://knight-s-hand-bot.onrender.com"  # 👈 замени на адрес своего проекта
    while True:
        try:
            requests.get(url)
            print("✅ Self-ping sent to keep the app alive")
        except Exception as e:
            print(f"⚠️ Ping failed: {e}")
        time.sleep(600)  # каждые 10 минут

# ===== 5. Запуск =====
if __name__ == "__main__":
    # Отдельные потоки: один для Flask, один для бота, один для пинга
    threading.Thread(target=keep_alive, daemon=True).start()
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()

    # Flask слушает порт Render-а
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)