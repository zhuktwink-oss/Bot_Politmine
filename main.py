import html
import asyncio
import logging
import json
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# --- КОНФИГУРАЦИЯ ---
TOKEN = "8226548122:AAHdyihHKdrXHZr4W8oFuxtNaY8tQriG4RE"
ADMIN_ID = 6131249570  # ЗАМЕНИ НА СВОЙ ID, ЧТОБЫ ПОЛУЧАТЬ ЗАЯВКИ
AD_INTERVAL = 43200  # 12 часов
AD_TEXT = "Подумай о будущем. Вступи в ряды Ординалистов: https://t.me/ordinalism"
DB_FILE = "database.json"

# --- ЛОГИРОВАНИЕ ---
logging.basicConfig(level=logging.INFO)

# --- БАЗА ДАННЫХ (ФАЙЛОВАЯ СИСТЕМА) ---
default_db = {
    "cities": {
        "city1": {
            "name": "Стальгорнский Рейх",
            "coords": "X: 100, Y: 64, Z: -200",
            "allies": "Республика Зюзя",
            "enemies": "Нет",
            "tasks": "1. Построить ферму ягод.",
            "jobs": {
                "miner": {"name": "Шахтер", "salary": "1000$", "slots": 5, "taken": 0, "desc": "Копать ресурсы."}
            },
            "shops": [
                {"name": "Пятерочка", "coords": "X: 105, Y: 64, Z: -190"},
                {"name": "Кузница", "coords": "X: 120, Y: 64, Z: -210"}
            ]
        },
        "city2": {
            "name": "Мрачный",
            "coords": "X: -500, Y: 70, Z: 300",
            "allies": "Нет",
            "enemies": "Солнечный",
            "tasks": "1. Укрепить стены.",
            "jobs": {
                "spy": {"name": "Шпион", "salary": "2000$", "slots": 1, "taken": 0, "desc": "Следить за врагами."}
            },
            "shops": []
        }
    },
    "users_jobs": {},  
    "all_users": []  # Храним как список для JSON
}

db = {}

def load_db():
    global db
    if not os.path.exists(DB_FILE):
        db = default_db
        save_db()
    else:
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                db = json.load(f)
            # Проверка целостности структуры (если добавили новые поля в коде)
            if "shops" not in db["cities"]["city1"]:
                for city in db["cities"].values():
                    if "shops" not in city:
                        city["shops"] = []
                save_db()
        except Exception as e:
            logging.error(f"Ошибка загрузки БД: {e}")
            db = default_db

def save_db():
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Ошибка сохранения БД: {e}")

# --- ИНИЦИАЛИЗАЦИЯ ---
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# --- МАШИНА СОСТОЯНИЙ (ДЛЯ ЗАЯВКИ) ---
class Form(StatesGroup):
    waiting_for_application = State()

# --- КЛАВИАТУРЫ ---

def get_main_menu():
    buttons = [
        [InlineKeyboardButton(text="🏪 Список магазинов", callback_data="menu_shops")],
        [InlineKeyboardButton(text="🏙 Список городов", callback_data="menu_cities")],
        [InlineKeyboardButton(text="📝 Отправить заявку", callback_data="menu_apply")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_cities_keyboard(action_prefix="city"):
    # action_prefix позволяет использовать один список для разных целей
    # "city" -> открывает меню города
    # "shoplist" -> открывает список магазинов города
    buttons = []
    for code, data in db["cities"].items():
        buttons.append([InlineKeyboardButton(text=data["name"], callback_data=f"{action_prefix}_{code}")])
    
    buttons.append([InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
def get_city_menu_keyboard(city_code, user_id=None):
    buttons = [
        [InlineKeyboardButton(text="💼 Работы", callback_data=f"jobs_{city_code}")],
        [InlineKeyboardButton(text="🏪 Магазины", callback_data=f"showshops_{city_code}")], # Новая кнопка
        [InlineKeyboardButton(text="🤝 Союзники", callback_data=f"allies_{city_code}")],
        [InlineKeyboardButton(text="⚔️ Враги", callback_data=f"enemies_{city_code}")],
        [InlineKeyboardButton(text="📍 Координаты", callback_data=f"coords_{city_code}")],
        [InlineKeyboardButton(text="📜 Задачи", callback_data=f"tasks_{city_code}")],
    ]
    
    # Проверяем работу (приводим user_id к строке, т.к. в JSON ключи словаря - строки)
    str_user_id = str(user_id)
    if str_user_id in db["users_jobs"]:
        user_job = db["users_jobs"][str_user_id]
        if user_job["city_code"] == city_code:
            buttons.append([InlineKeyboardButton(text="🚫 Уволиться", callback_data=f"quitjob_{city_code}")])
    
    buttons.append([InlineKeyboardButton(text="🔙 К списку городов", callback_data="menu_cities")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_jobs_keyboard(city_code, user_id):
    buttons = []
    city_jobs = db["cities"][city_code]["jobs"]
    str_user_id = str(user_id)
    
    for job_code, info in city_jobs.items():
        free_slots = info['slots'] - info['taken']
        status = "✅" if free_slots > 0 else "❌"
        text = f"{status} {info['name']} ({info['salary']}) [{info['taken']}/{info['slots']}]"
        
        user_has_job = str_user_id in db["users_jobs"]
        
        if free_slots > 0 and not user_has_job:
            buttons.append([InlineKeyboardButton(text=text, callback_data=f"takejob_{city_code}_{job_code}")])
        else:
            buttons.append([InlineKeyboardButton(text=text + " (Недоступно)", callback_data="ignore")])
            
    buttons.append([InlineKeyboardButton(text="🔙 Назад в город", callback_data=f"city_{city_code}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- УТИЛИТЫ ---
def add_user_to_db(user_id):
    if user_id not in db["all_users"]:
        db["all_users"].append(user_id)
        save_db()

# --- ХЕНДЛЕРЫ: ОСНОВНОЕ ---

@dp.message(Command("start"))
async def cmd_start(message: Message):
    add_user_to_db(message.from_user.id)
    await message.answer(
        "👋 Привет! Добро пожаловать в систему Ординализма.\nВыбери действие:", 
        reply_markup=get_main_menu()
    )

@dp.callback_query(F.data == "main_menu")
async def back_to_main(callback: CallbackQuery):
    await callback.message.edit_text("Выбери действие:", reply_markup=get_main_menu())

# --- ХЕНДЛЕРЫ: МЕНЮ МАГАЗИНОВ ---

@dp.callback_query(F.data == "menu_shops")
async def menu_shops_list(callback: CallbackQuery):
    await callback.message.edit_text(
        "🏪 Список магазинов\nВыберите город, чтобы посмотреть магазины:",
        reply_markup=get_cities_keyboard(action_prefix="shoplist"),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("shoplist_"))
async def show_shops_in_city(callback: CallbackQuery):
    city_code = callback.data.split("_")[1]
    city = db["cities"][city_code]
    shops = city.get("shops", [])
    
    text = f"🏪 Магазины в г. {city['name']}:\n\n"
    if not shops:
        text += "В этом городе пока нет магазинов."
    else:
        for shop in shops:
            text += f"🛒 {shop['name']}\n📍 {shop['coords']}\n\n"
    
    # Кнопка назад
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 К выбору города", callback_data="menu_shops")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

# Дублирующая логика для кнопки внутри меню города
@dp.callback_query(F.data.startswith("showshops_"))

async def show_shops_internal(callback: CallbackQuery):
    city_code = callback.data.split("_")[1]
    city = db["cities"][city_code]
    shops = city.get("shops", [])
    
    text = f"🏪 Магазины в г. {city['name']}:\n\n"
    if not shops:
        text += "В этом городе пока нет магазинов."
    else:
        for shop in shops:
            text += f"🛒 {shop['name']}\n📍 {shop['coords']}\n\n"
            
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад в город", callback_data=f"city_{city_code}")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


# --- ХЕНДЛЕРЫ: МЕНЮ ГОРОДОВ (Старая логика) ---

@dp.callback_query(F.data == "menu_cities")
async def menu_cities_list(callback: CallbackQuery):
    await callback.message.edit_text(
        "🏙 Список городов\nВыберите город:", 
        reply_markup=get_cities_keyboard(action_prefix="city"),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("city_"))
async def show_city_menu(callback: CallbackQuery):
    city_code = callback.data.split("_")[1]
    city_name = db["cities"][city_code]["name"]
    user_id = callback.from_user.id
    
    text = f"🏙 Город: {city_name}\nВыберите раздел:"
    await callback.message.edit_text(text, reply_markup=get_city_menu_keyboard(city_code, user_id), parse_mode="Markdown")

@dp.callback_query(F.data.startswith(("allies_", "enemies_", "coords_", "tasks_")))
async def show_info(callback: CallbackQuery):
    parts = callback.data.split("_", 1)
    action = parts[0]
    city_code = parts[1]
    
    city_data = db["cities"][city_code]
    info_map = {
        "allies": f"🤝 Союзники:\n{city_data['allies']}",
        "enemies": f"⚔️ Враги:\n{city_data['enemies']}",
        "coords": f"📍 Координаты спавна:\n{city_data['coords']}",
        "tasks": f"📜 Задачи города:\n{city_data['tasks']}"
    }
    
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data=f"city_{city_code}")]])
    await callback.message.edit_text(info_map[action], reply_markup=back_kb, parse_mode="Markdown")

# --- ХЕНДЛЕРЫ: ЗАЯВКА НА ДОБАВЛЕНИЕ ГОРОДА ---

@dp.callback_query(F.data == "menu_apply")
async def start_application(callback: CallbackQuery, state: FSMContext):
    text = (
        "📝 Заявка на добавление города\n\n"
        "Пожалуйста, напишите одним сообщением следующую информацию:\n"
        "1. Название города\n"
        "2. Координаты\n"
        "3. Владелец/Мэр\n"
        "4. Краткое описание\n\n"
        "Напишите 'отмена', чтобы вернуться."
    )
    await callback.message.edit_text(text, parse_mode="Markdown")
    await state.set_state(Form.waiting_for_application)

@dp.message(Form.waiting_for_application)
async def process_application(message: Message, state: FSMContext):
    if message.text.lower() == 'отмена':
        await state.clear()
        await message.answer("Заявка отменена.", reply_markup=get_main_menu())
        return

    application_text = message.text
    user = message.from_user
    
    # Используем html.escape, чтобы спецсимволы в именах не ломали сообщение
    # И меняем разметку на HTML (<b> - жирный, <code> - код)
    
    safe_name = html.escape(user.full_name)
    safe_username = html.escape(str(user.username))
    safe_text = html.escape(application_text)

    admin_msg = (
        f"📩 <b>НОВАЯ ЗАЯВКА НА ГОРОД!</b>\n\n"
        f"👤 От: {safe_name} (@{safe_username})\n"
        f"🆔 ID: <code>{user.id}</code>\n\n"
        f"📄 <b>Текст заявки:</b>\n{safe_text}"
    )
    
    try:
        # Важно: parse_mode="HTML"
        await bot.send_message(ADMIN_ID, admin_msg, parse_mode="HTML")
        await message.answer("✅ Заявка успешно отправлена!\nАдминистратор рассмотрит её в ближайшее время.", reply_markup=get_main_menu(), parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"Ошибка отправки: {e}. Попробуйте позже.")
        logging.error(f"Не удалось отправить заявку админу: {e}")
    
    await state.clear()

# --- ХЕНДЛЕРЫ: РАБОТА (С сохранением в БД) ---

@dp.callback_query(F.data.startswith("jobs_"))
async def show_jobs(callback: CallbackQuery):
    city_code = callback.data.split("_")[1]
    user_id = callback.from_user.id
    text = "💼 Биржа труда\nНажмите на вакансию, чтобы устроиться:"
    await callback.message.edit_text(text, reply_markup=get_jobs_keyboard(city_code, user_id), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("takejob_"))
async def take_job(callback: CallbackQuery):
    parts = callback.data.split("_")
    city_code = parts[1]
    job_code = parts[2]
    user_id = callback.from_user.id
    str_user_id = str(user_id) # JSON ключи - строки
    
    if str_user_id in db["users_jobs"]:
        await callback.answer("Вы уже работаете! Сначала увольтесь.", show_alert=True)
        return
    
    job_info = db["cities"][city_code]["jobs"][job_code]
    
    if job_info["taken"] >= job_info["slots"]:
        await callback.answer("Места уже закончились!", show_alert=True)
        return

    # Логика устройства
    job_info["taken"] += 1
    db["users_jobs"][str_user_id] = {"city_code": city_code, "job_code": job_code}
    save_db() # СОХРАНЯЕМ В ФАЙЛ
    
    congrats_text = (
        f"🎉 Поздравляю!\n"
        f"Вы приняты на должность: {job_info['name']}\n"
        f"Зарплата: {job_info['salary']}\n\n"
        f"📝 Ваши обязанности:\n{job_info['desc']}"
    )
    await callback.message.edit_text(congrats_text, reply_markup=get_jobs_keyboard(city_code, user_id), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("quitjob_"))
async def quit_job(callback: CallbackQuery):
    city_code = callback.data.split("_")[1]
    user_id = callback.from_user.id
    str_user_id = str(user_id)
    
    if str_user_id not in db["users_jobs"]:
        await callback.answer("Вы не работаете!", show_alert=True)
        return
    
    user_job = db["users_jobs"][str_user_id]
    
    # Увольняем
    job_code = user_job["job_code"]
    job_info = db["cities"][city_code]["jobs"][job_code]
    job_info["taken"] -= 1
    del db["users_jobs"][str_user_id]
    save_db() # СОХРАНЯЕМ В ФАЙЛ
    
    await callback.answer("Вы уволились с работы!", show_alert=True)
    
    city_name = db["cities"][city_code]["name"]
    text = f"🏙 Город: {city_name}\nВыберите раздел:"
    await callback.message.edit_text(text, reply_markup=get_city_menu_keyboard(city_code, user_id), parse_mode="Markdown")

@dp.callback_query(F.data == "ignore")
async def ignore_click(callback: CallbackQuery):
    await callback.answer("Эта вакансия недоступна!")

# --- РАССЫЛКА И АДМИНКА ---
@dp.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    text = message.text.replace('/broadcast', '').strip()
    if not text:
        await message.answer("Текст?")
        return
    
    count = 0
    # Создаем копию списка, чтобы избежать ошибок изменения во время итерации
    users = list(db["all_users"]) 
    for user_id in users:
        try:
            await bot.send_message(user_id, text)
            count += 1
            await asyncio.sleep(0.05)
        except:
            pass
    await message.answer(f"Отправлено: {count}")

async def broadcaster():
    while True:
        await asyncio.sleep(AD_INTERVAL)
        users = list(db["all_users"])
        for user_id in users:
            try:
                await bot.send_message(user_id, AD_TEXT)
            except:
                pass
            await asyncio.sleep(0.05)

# --- ЗАПУСК ---
async def main():
    load_db() # Загружаем базу при старте
    print("Бот запущен...")
    asyncio.create_task(broadcaster())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())