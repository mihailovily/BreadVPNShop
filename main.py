import telebot
from telebot import types
import json
import os

TOKEN = open("creds/TOKEN.txt", "r").read().strip()
ADMIN_ID = open("creds/ADMIN_ID.txt", "r").read().strip()
ACCESS_PASSWORD = open("creds/PASSWORD.txt", "r").read().strip()
USERS_FILE = "users.json"

bot = telebot.TeleBot(TOKEN)

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_users():
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

users = load_users()

def main_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📁 Запросить конфиг", "💰 Подтвердить оплату")
    return kb

def admin_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📤 Рассылка", "📨 Отправить конфиг", "💬 Напомнить об оплате")
    return kb

# === Команды ===
@bot.message_handler(commands=["start"])
def start(msg):
    if msg.chat.id == ADMIN_ID:
        bot.send_message(msg.chat.id, "Привет, админ!", reply_markup=admin_keyboard())
        return

    username = msg.from_user.username or str(msg.chat.id)
    if username in users:
        bot.send_message(msg.chat.id, "С возвращением!", reply_markup=main_keyboard())
    else:
        bot.send_message(msg.chat.id, "🔐 Введи пароль для доступа к боту:")
        bot.register_next_step_handler(msg, check_password)

def check_password(msg):
    if msg.text.strip() == ACCESS_PASSWORD:
        username = msg.from_user.username or str(msg.chat.id)
        users[username] = msg.chat.id
        save_users()
        bot.send_message(msg.chat.id, "✅ Доступ разрешён. Добро пожаловать!", reply_markup=main_keyboard())
        bot.send_message(ADMIN_ID, f"👤 Новый пользователь: @{username}")
    else:
        bot.send_message(msg.chat.id, "❌ Неверный пароль. Попробуй снова.")
        bot.register_next_step_handler(msg, check_password)

@bot.message_handler(func=lambda m: m.text == "📁 Запросить конфиг")
def request_config(msg):
    username = msg.from_user.username or str(msg.chat.id)
    bot.send_message(ADMIN_ID, f"📥 @{username} запросил конфиг.")
    bot.send_message(msg.chat.id, "Запрос отправлен админу. Ожидай ответ!")

@bot.message_handler(func=lambda m: m.text == "💰 Подтвердить оплату")
def confirm_payment(msg):
    username = msg.from_user.username or str(msg.chat.id)
    bot.send_message(ADMIN_ID, f"💸 @{username} подтвердил оплату.")
    bot.send_message(msg.chat.id, "Спасибо! Админ скоро проверит оплату.")

def format_user_list():
    text = ""
    for i, username in enumerate(users.keys(), 1):
        text += f"{i}. @{username}\n"
    return text or "⚠️ Нет зарегистрированных пользователей."

def get_username_by_index(idx):
    try:
        idx = int(idx)
        return list(users.keys())[idx - 1]
    except:
        return None

# === Админ ===
@bot.message_handler(func=lambda m: m.chat.id == ADMIN_ID and m.text == "📤 Рассылка")
def broadcast_start(msg):
    bot.send_message(msg.chat.id, "Введи текст рассылки:")
    bot.register_next_step_handler(msg, broadcast_send)

def broadcast_send(msg):
    text = msg.text
    dead = []
    for username, uid in users.items():
        try:
            bot.send_message(uid, f"📢 {text}")
        except Exception as e:
            dead.append(username)
            print(f"Ошибка при рассылке @{username}: {e}")
    if dead:
        for d in dead:
            users.pop(d, None)
        save_users()
        bot.send_message(ADMIN_ID, f"⚠️ Удалены неактивные пользователи: {', '.join(dead)}")
    bot.send_message(ADMIN_ID, "✅ Рассылка завершена.")

@bot.message_handler(func=lambda m: m.chat.id == ADMIN_ID and m.text == "📨 Отправить конфиг")
def send_config_start(msg):
    text = "Выбери пользователя:\n" + format_user_list()
    bot.send_message(msg.chat.id, text)
    bot.send_message(msg.chat.id, "Введи номер или @username:")
    bot.register_next_step_handler(msg, ask_config_file)

def ask_config_file(msg):
    username = msg.text.strip().lstrip("@")
    if username.isdigit():
        username = get_username_by_index(username)
    if username and username in users:
        bot.send_message(msg.chat.id, f"Теперь отправь файл конфига для @{username}:")
        bot.register_next_step_handler(msg, send_config_file, username)
    else:
        bot.send_message(msg.chat.id, "❌ Пользователь не найден. Попробуй снова.")

def send_config_file(msg, username):
    if msg.document:
        file_id = msg.document.file_id
        bot.send_document(users[username], file_id, caption="📎 Твой VPN-конфиг. Спасибо за оплату!")
        bot.send_message(ADMIN_ID, f"✅ Конфиг отправлен @{username}.")
    else:
        bot.send_message(ADMIN_ID, "⚠ Нужно отправить именно файл.")

@bot.message_handler(func=lambda m: m.chat.id == ADMIN_ID and m.text == "💬 Напомнить об оплате")
def remind_payment(msg):
    text = "Кому напомнить?\n" + format_user_list()
    bot.send_message(msg.chat.id, text)
    bot.send_message(msg.chat.id, "Введи номер или @username:")
    bot.register_next_step_handler(msg, remind_payment_send)

def remind_payment_send(msg):
    username = msg.text.strip().lstrip("@")
    if username.isdigit():
        username = get_username_by_index(username)
    if username and username in users:
        bot.send_message(users[username], "💰 Напоминаем: необходимо подтвердить оплату для получения конфига.")
        bot.send_message(ADMIN_ID, f"✅ Напоминание отправлено @{username}.")
    else:
        bot.send_message(ADMIN_ID, "❌ Пользователь не найден.")

bot.polling(none_stop=True)
