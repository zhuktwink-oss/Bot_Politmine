import asyncio
import logging
import os
import sqlite3
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

# --- КОНФИГУРАЦИЯ ---
TOKEN = "8226548122:AAHdyihHKdrXHZr4W8oFuxtNaY8tQriG4RE"  # Ваш токен
AD_INTERVAL = 43200  # 12 часов
AD_TEXT = "Подумай о будущем. Такими темпами тебе будет нелегко жить, пока в стране царствует авторитарное самодержавие. Исправь это и вступи в ряды Ординалистов, а заходно узнай, что это. https://t.me/ordinalism"

# Bothost даст вашему боту URL вида: https://ваш-бот.bothost.ru
# ЗАМЕНИТЕ ЭТУ СТРОКУ НА ВАШ РЕАЛЬНЫЙ URL ПОСЛЕ ДЕПЛОЯ!
BASE_WEBHOOK_URL = "https://ваш-бот.bothost.ru"
WEBHOOK_PATH = "/webhook"

# --- НАСТРОЙКА БАЗЫ ДАННЫХ SQLite ---

def init_db():
    # Получаем путь к базе данных из переменной окружения, если она задана
    db_path = os.environ.get('DATABASE_PATH', 'bot_database.db')
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    # Таблица для хранения данных городов
    cur.execute('''
        CREATE TABLE IF NOT EXISTS cities (
            code TEXT PRIMARY KEY,
            name TEXT,
            coords TEXT,
            allies TEXT,
            enemies TEXT,
            tasks TEXT
        )
    ''')
    # Таблица для хранения вакансий
    cur.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city_code TEXT,
            job_code TEXT,
            name TEXT,
            salary TEXT,
            slots INTEGER,
            taken INTEGER,
            desc TEXT,
            FOREIGN KEY (city_code) REFERENCES cities (code)
        )
    ''')
    # Таблица для связи пользователь-работа
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users_jobs (
            user_id INTEGER PRIMARY KEY,
            city_code TEXT,
            job_code TEXT
        )
    ''')
    # Таблица для списка пользователей рассылки
    cur.execute('''
        CREATE TABLE IF NOT EXISTS all_users (
            user_id INTEGER PRIMARY KEY
        )
    ''')
    conn.commit()
    conn.close()

# Инициализируем базу данных при импорте модуля
init_db()

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ С БАЗОЙ ---
def db_execute(query, params=(), fetch=False):
    """Выполняет SQL-запрос и возвращает результат если нужно."""
    conn = sqlite3.connect('bot_database.db')
    cur = conn.cursor()
    cur.execute(query, params)
    if fetch:
        result = cur.fetchall()
    else:
        result = None
    conn.commit()
    conn.close()
    return result

# --- ИНИЦИАЛИЗАЦИЯ БОТА ---
bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# --- ВАШИ ФУНКЦИИ КЛАВИАТУР (из ai_studio_code4.py) ---
def get_cities_keyboard():
    # Достаём список городов из базы данных
    cities = db_execute("SELECT code, name FROM cities", fetch=True)
    buttons = []
    for city_code, city_name in cities:
        buttons.append([InlineKeyboardButton(text=city_name, callback_data=f"city_{city_code}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_city_menu_keyboard(city_code, user_id=None):
    buttons = [
        [InlineKeyboardButton(text="💼 Работы", callback_data=f"jobs_{city_code}")],
        [InlineKeyboardButton(text="🤝 Союзники", callback_data=f"allies_{city_code}")],
        [InlineKeyboardButton(text="⚔️ Враги", callback_data=f"enemies_{city_code}")],
        [InlineKeyboardButton(text="📍 Координаты", callback_data=f"coords_{city_code}")],
        [InlineKeyboardButton(text="📜 Задачи", callback_data=f"tasks_{city_code}")],
    ]
    # Проверяем, работает ли пользователь уже в этом городе (из базы данных)
    user_job = db_execute("SELECT city_code FROM users_jobs WHERE user_id = ?", (user_id,), fetch=True)

Kr. B., [26.12.2025 18:39]
if user_job and user_job[0][0] == city_code:
        buttons.append([InlineKeyboardButton(text="🚫 Уволиться", callback_data=f"quitjob_{city_code}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад к выбору города", callback_data="back_to_start")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_jobs_keyboard(city_code, user_id):
    buttons = []
    # Достаём список вакансий для города из базы
    jobs = db_execute(
        "SELECT job_code, name, salary, slots, taken, desc FROM jobs WHERE city_code = ?",
        (city_code,), fetch=True
    )
    # Проверяем, работает ли пользователь уже где-то
    user_has_job = db_execute("SELECT 1 FROM users_jobs WHERE user_id = ?", (user_id,), fetch=True)
    for job_code, name, salary, slots, taken, desc in jobs:
        free_slots = slots - taken
        status = "✅" if free_slots > 0 else "❌"
        text = f"{status} {name} ({salary}) [{taken}/{slots}]"
        if free_slots > 0 and not user_has_job:
            buttons.append([InlineKeyboardButton(text=text, callback_data=f"takejob_{city_code}_{job_code}")])
        else:
            buttons.append([InlineKeyboardButton(text=text + " (Недоступно)", callback_data="ignore")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад в город", callback_data=f"city_{city_code}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def add_user_to_broadcast(user_id):
    """Добавляет пользователя в список для рассылки (в базу данных)"""
    try:
        db_execute("INSERT OR IGNORE INTO all_users (user_id) VALUES (?)", (user_id,))
        count = db_execute("SELECT COUNT(*) FROM all_users", fetch=True)[0][0]
        print(f"Пользователь добавлен в рассылку: {user_id} (Всего: {count})")
    except Exception as e:
        print(f"Ошибка добавления пользователя {user_id}: {e}")

# --- НАЧАЛЬНАЯ ЗАГРУЗКА ДАННЫХ В БАЗУ ---
def load_initial_data():
    """Загружает стартовые данные о городах и работах в базу, если она пуста."""
    # Проверяем, есть ли уже города в базе
    existing_cities = db_execute("SELECT COUNT(*) FROM cities", fetch=True)[0][0]
    if existing_cities > 0:
        return  # Данные уже есть, выходим
    print("Загружаем начальные данные в базу...")
    # Данные города 1
    db_execute(
        "INSERT INTO cities (code, name, coords, allies, enemies, tasks) VALUES (?, ?, ?, ?, ?, ?)",
        ('city1', 'Стальгорнский Рейх', 'X: 100, Y: 64, Z: -200', 'Республика Зюзя', 'Нет', '1. Построить ферму ягод за складом на /outpost.\n2. ')
    )
    # Вакансии для города 1
    db_execute(
        "INSERT INTO jobs (city_code, job_code, name, salary, slots, taken, desc) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ('city1', 'miner', 'Шахтер', '1000$', 5, 2, 'Копать ресурсы в шахте.')
    )
    db_execute(
        "INSERT INTO jobs (city_code, job_code, name, salary, slots, taken, desc) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ('city1', 'guard', 'Стражник', '1500$', 2, 0, 'Охранять ворота от монстров.')
    )
    # Данные города 2
    db_execute(
        "INSERT INTO cities (code, name, coords, allies, enemies, tasks) VALUES (?, ?, ?, ?, ?, ?)",
        ('city2', 'Мрачный', 'X: -500, Y: 70, Z: 300', 'Нет', 'Солнечный', '1. Укрепить стены.\n2. Найти шпиона.')
    )
    # Вакансии для города 2
    db_execute(
        "INSERT INTO jobs (city_code, job_code, name, salary, slots, taken, desc) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ('city2', 'spy', 'Шпион', '2000$', 1, 0, 'Следить за врагами.')
    )
    print("Начальные данные загружены.")

# Вызываем загрузку начальных данных
load_initial_data()

# --- ВАШИ ОБРАБОТЧИКИ (основная логика бота из ai_studio_code4.py) ---
# Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    add_user_to_broadcast(user_id)
    await message.answer("Привет! Выбери город:", reply_markup=get_cities_keyboard())

Kr. B., [26.12.2025 18:39]
# Обработчик команды /broadcast (для админа)
@dp.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    if message.from_user.id != 6131249570:  # Замените на ваш ID
        await message.answer("У вас нет прав для этой команды.")
        return
    broadcast_text = message.text.replace('/broadcast', '').strip()
    if not broadcast_text:
        await message.answer("Использование: /broadcast ваш текст рассылки")
        return
    await send_broadcast(broadcast_text)
    await message.answer(f"Рассылка отправлена пользователям")

# Обработчик команды /stats
@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    if message.from_user.id != 6131249570:  # Замените на ваш ID
        await message.answer("У вас нет прав для этой команды.")
        return
    total_users = db_execute("SELECT COUNT(*) FROM all_users", fetch=True)[0][0]
    total_workers = db_execute("SELECT COUNT(*) FROM users_jobs", fetch=True)[0][0]
    total_cities = db_execute("SELECT COUNT(*) FROM cities", fetch=True)[0][0]
    stats_text = (
        f"📊 Статистика бота:\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"💼 Работающих: {total_workers}\n"
        f"🏙 Городов: {total_cities}"
    )
    await message.answer(stats_text)

# Обработчик кнопки "Назад к выбору города"
@dp.callback_query(F.data == "back_to_start")
async def go_back(callback: CallbackQuery):
    add_user_to_broadcast(callback.from_user.id)
    await callback.message.edit_text("Выбери город:", reply_markup=get_cities_keyboard())

# Обработчик выбора города
@dp.callback_query(F.data.startswith("city_"))
async def show_city_menu(callback: CallbackQuery):
    add_user_to_broadcast(callback.from_user.id)
    city_code = callback.data.split("_")[1]
    city_name = db_execute("SELECT name FROM cities WHERE code = ?", (city_code,), fetch=True)[0][0]
    user_id = callback.from_user.id
    text = f"🏙 Город: {city_name}\nВыберите раздел:"
    await callback.message.edit_text(text, reply_markup=get_city_menu_keyboard(city_code, user_id), parse_mode="Markdown")

# Обработчик информации (союзники, враги, координаты, задачи)
@dp.callback_query(F.data.startswith(("allies_", "enemies_", "coords_", "tasks_")))
async def show_info(callback: CallbackQuery):
    add_user_to_broadcast(callback.from_user.id)
    parts = callback.data.split("_", 1)
    action = parts[0]
    city_code = parts[1]
    # Достаём данные города из базы
    city_data = db_execute(
        "SELECT name, coords, allies, enemies, tasks FROM cities WHERE code = ?",
        (city_code,), fetch=True
    )[0]
    info_map = {
        "allies": f"🤝 Союзники:\n{city_data[2]}",
        "enemies": f"⚔️ Враги:\n{city_data[3]}",
        "coords": f"📍 Координаты спавна:\n{city_data[1]}",
        "tasks": f"📜 Задачи города:\n{city_data[4]}"
    }
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data=f"city_{city_code}")]])
    await callback.message.edit_text(info_map[action], reply_markup=back_kb, parse_mode="Markdown")

# Обработчик просмотра работ
@dp.callback_query(F.data.startswith("jobs_"))
async def show_jobs(callback: CallbackQuery):
    add_user_to_broadcast(callback.from_user.id)
    city_code = callback.data.split("_")[1]
    user_id = callback.from_user.id
    text = "💼 Биржа труда\nНажмите на вакансию, чтобы устроиться:"
    await callback.message.edit_text(text, reply_markup=get_jobs_keyboard(city_code, user_id), parse_mode="Markdown")

# Обработчик устройства на работу
@dp.callback_query(F.data.startswith("takejob_"))
async def take_job(callback: CallbackQuery):
    add_user_to_broadcast(callback.from_user.id)
    parts = callback.data.split("_")
    city_code = parts[1]
    job_code = parts[2]
    user_id = callback.from_user.id

Kr. B., [26.12.2025 18:39]
# Проверяем, не работает ли пользователь уже
    if db_execute("SELECT 1 FROM users_jobs WHERE user_id = ?", (user_id,), fetch=True):
        await callback.answer("Вы уже работаете! Сначала увольтесь.", show_alert=True)
        return
    # Проверяем, есть ли свободные места
    job_info = db_execute(
        "SELECT slots, taken FROM jobs WHERE city_code = ? AND job_code = ?",
        (city_code, job_code), fetch=True
    )[0]
    if job_info[1] >= job_info[0]:
        await callback.answer("Места уже закончились!", show_alert=True)
        return
    # Устраиваем на работу: увеличиваем счетчик и добавляем запись о пользователе
    new_taken = job_info[1] + 1
    db_execute(
        "UPDATE jobs SET taken = ? WHERE city_code = ? AND job_code = ?",
        (new_taken, city_code, job_code)
    )
    db_execute(
        "INSERT INTO users_jobs (user_id, city_code, job_code) VALUES (?, ?, ?)",
        (user_id, city_code, job_code)
    )
    # Формируем сообщение об успехе
    job_full_info = db_execute(
        "SELECT name, salary, desc FROM jobs WHERE city_code = ? AND job_code = ?",
        (city_code, job_code), fetch=True
    )[0]
    congrats_text = (
        f"🎉 Поздравляю!\n"
        f"Вы приняты на должность: {job_full_info[0]}\n"
        f"Зарплата: {job_full_info[1]}\n\n"
        f"📝 Ваши обязанности:\n{job_full_info[2]}"
    )
    await callback.message.edit_text(congrats_text, reply_markup=get_jobs_keyboard(city_code, user_id), parse_mode="Markdown")
    await callback.answer()

# Обработчик увольнения с работы
@dp.callback_query(F.data.startswith("quitjob_"))
async def quit_job(callback: CallbackQuery):
    add_user_to_broadcast(callback.from_user.id)
    city_code = callback.data.split("_")[1]
    user_id = callback.from_user.id
    # Проверяем, работает ли пользователь в этом городе
    user_job = db_execute(
        "SELECT job_code FROM users_jobs WHERE user_id = ? AND city_code = ?",
        (user_id, city_code), fetch=True
    )
    if not user_job:
        await callback.answer("Вы не работаете в этом городе!", show_alert=True)
        return
    job_code = user_job[0][0]
    # Увольняем: уменьшаем счетчик и удаляем запись о пользователе
    current_taken = db_execute(
        "SELECT taken FROM jobs WHERE city_code = ? AND job_code = ?",
        (city_code, job_code), fetch=True
    )[0][0]
    db_execute(
        "UPDATE jobs SET taken = ? WHERE city_code = ? AND job_code = ?",
        (current_taken - 1, city_code, job_code)
    )
    db_execute("DELETE FROM users_jobs WHERE user_id = ?", (user_id,))
    await callback.answer("Вы уволились с работы!", show_alert=True)
    # Обновляем меню города
    city_name = db_execute("SELECT name FROM cities WHERE code = ?", (city_code,), fetch=True)[0][0]
    text = f"🏙 Город: {city_name}\nВыберите раздел:"
    await callback.message.edit_text(text, reply_markup=get_city_menu_keyboard(city_code, user_id), parse_mode="Markdown")

# Заглушка для неактивных кнопок
@dp.callback_query(F.data == "ignore")
async def ignore_click(callback: CallbackQuery):
    add_user_to_broadcast(callback.from_user.id)
    await callback.answer("Эта вакансия недоступна!")

# --- РАССЫЛКА И АВТО-РЕКЛАМА ---
async def send_broadcast(text):
    """Отправляет рассылку всем пользователям из базы данных."""
    users = db_execute("SELECT user_id FROM all_users", fetch=True)
    success = 0
    for (user_id,) in users:
        try:
            await bot.send_message(user_id, text)
            success += 1
        except Exception as e:
            print(f"Ошибка отправки пользователю {user_id}: {e}")
            # Можно удалить недоступного пользователя из базы
            db_execute("DELETE FROM all_users WHERE user_id = ?", (user_id,))
        await asyncio.sleep(0.1)  # Пауза, чтобы не превысить лимиты Telegram
    print(f"Рассылка завершена. Успешно отправлено: {success}")

Kr. B., [26.12.2025 18:39]
async def broadcaster():
    """Фоновая задача для автоматической рассылки рекламы."""
    while True:
        await asyncio.sleep(AD_INTERVAL)
        print(f"[АВТО-РЕКЛАМА] Отправка...")
        await send_broadcast(AD_TEXT)

# --- НАСТРОЙКА ВЕБХУКОВ И ЗАПУСК СЕРВЕРА ---
async def on_startup(bot: Bot):
    """Действия при запуске: устанавливаем вебхук и запускаем рассылку."""
    webhook_url = f"{BASE_WEBHOOK_URL}{WEBHOOK_PATH}"
    await bot.set_webhook(webhook_url)
    logging.info(f"✅ Вебхук установлен на {webhook_url}")
    asyncio.create_task(broadcaster())

async def on_shutdown(bot: Bot):
    """Действия при завершении: удаляем вебхук."""
    logging.warning("Завершение работы...")
    await bot.delete_webhook()
    await bot.session.close()
    logging.warning("Бот остановлен.")

async def main():
    """Основная функция для запуска веб-сервера."""
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    app = web.Application()
    webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot, secret_token=None)
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))  # Bothost сам подставляет порт
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()
    logging.info(f"🚀 Сервер запущен. Ожидаем запросы по пути: {WEBHOOK_PATH}")
    await asyncio.Event().wait()  # Бесконечное ожидание

if name == "main":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Работа приложения остановлена вручную.")