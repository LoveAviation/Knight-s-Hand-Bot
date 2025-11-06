import os
import threading
import time
import requests
from io import BytesIO
from PIL import Image
from flask import Flask
import telebot
import requests

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN не задан. Установите переменную окружения.")

bot = telebot.TeleBot(TOKEN)
BOT_NAME = "рука рыцаря"

# ===== 2. Flask сервер =====
app = Flask(__name__)

@app.route('/')
def home():
    return "I'm alive!"  # Render проверяет, жив ли сервер

canvas_command = "Холст сюда!"
test_command = "Ты жив?"

def requiring_canvas(msg) -> bool:
    """
    Проверяет, содержит ли сообщение слова 'холст' и 'сюда'
    (игнорируя регистр, порядок и местоположение).
    """
    # Проверяем, что у сообщения вообще есть текст
    if not hasattr(msg, "text") or not msg.text:
        return False

    text = msg.text.lower()
    return "холст" in text

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id,"Привет! \nЯ пока что могу только подносить холст в чат группы, но надеюсь смогу большее!")

@bot.message_handler(commands=['alive'])
def is_alive(message):
    bot.send_message(message.chat.id,"Сэр, я жив!")

@bot.message_handler(content_types=['text'])
def text_messages(message):
    if requiring_canvas(message):
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
    else:
        text = message.text.lower()

        if BOT_NAME not in text:
            return

        prompt = text.replace(BOT_NAME, "").strip()
        if not prompt:
            prompt = "Привет! Что хочешь спросить?"

        bot.send_chat_action(message.chat.id, 'typing')

        answer = ask_ai_verbose(prompt)
        bot.send_message(message.chat.id, answer)

# ===== 4. Keep-alive (самопинг) =====
def keep_alive():
    """
    Функция каждые 10 минут пингует сам Render-сервис,
    чтобы сервер не "уснул".
    """
    url = "https://knight-s-hand-bot.onrender.com"
    while True:
        try:
            requests.get(url)
            print("✅ Self-ping sent to keep the app alive")
        except Exception as e:
            print(f"⚠️ Ping failed: {e}")
        time.sleep(600)  # каждые 10 минут


def ask_ai_verbose(prompt):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        # Используем надежную модель
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    # Инициализируем r вне try, чтобы к нему можно было обратиться в except
    r = None

    try:
        r = requests.post(url, json=data, headers=headers, timeout=30)

        # 1. КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Проверка статуса HTTP-ответа
        r.raise_for_status()

        response_json = r.json()

        if "choices" in response_json and len(response_json["choices"]) > 0:
            return response_json["choices"][0]["message"]["content"]
        else:
            # Сюда попадем, если запрос успешен (200), но ответа нет
            return "Ошибка работы с ИИ: Не удалось получить ожидаемый контент."

    except requests.exceptions.HTTPError as e:
        # 2. ОБРАБОТКА ОШИБОК API (401, 404, 429 и т.д.)
        # Выводим статус-код и текст ответа Groq
        status_code = r.status_code if r is not None else "Неизвестно"
        error_text = r.text if r is not None else str(e)

        # Используем f-строку для форматирования
        detailed_error = f"Ошибка работы с ИИ: API вернул ошибку {status_code}. Ответ: {error_text}"
        print(f"DEBUG: {detailed_error}")
        return detailed_error

    except requests.exceptions.RequestException as e:
        # 3. ОБРАБОТКА ОШИБОК СЕТИ/ТАЙМАУТА
        # Выводим тип сетевой ошибки (например, ConnectionError, Timeout)
        detailed_error = f"Ошибка работы с ИИ: Проблема с подключением к сети или таймаут. Детали: {type(e).__name__} - {e}"
        print(f"DEBUG: {detailed_error}")
        return detailed_error

    except Exception as e:
        # 4. Общая обработка других ошибок (например, неверный формат JSON)
        # Выводим общее сообщение об ошибке
        detailed_error = f"Ошибка работы с ИИ: Непредвиденная проблема. Детали: {type(e).__name__} - {e}"
        print(f"DEBUG: {detailed_error}")
        return detailed_error


# ===== 5. Запуск =====
if __name__ == "__main__":
    # Отдельные потоки: один для Flask, один для бота, один для пинга
    threading.Thread(target=keep_alive, daemon=True).start()
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()

    # Flask слушает порт Render-а
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)