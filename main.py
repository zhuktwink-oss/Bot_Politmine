import asyncio
import logging
import json
import os
import html
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# --- КОНФИГУРАЦИЯ ---
TOKEN = "8226548122:AAHdyihHKdrXHZr4W8oFuxtNaY8tQriG4RE"
ADMIN_ID = 6131249570  # <--- ТВОЙ ID
AD_INTERVAL = 129600  # 36 часов
AD_TEXT = "Мой Ютуб: https://youtube.com/@megakruiiiutel?si=EwNMi2obVaqA_hJs. Если вы хотите подобную рекламу своего города/магаза в боте, пишите: @megakruiii"
DB_FILE = "database.json"

# --- ЛОГИРОВАНИЕ ---
logging.basicConfig(level=logging.INFO)

# --- ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ДЛЯ ТАЙМЕРОВ ---
pending_notifications = {}

# --- БАЗА ДАННЫХ (ФАЙЛОВАЯ СИСТЕМА) ---
default_db = {
    "cities": {
        "city1": {
            "name": "Стальгорнскiй Ординатъ",
            "owner_id": ADMIN_ID,
            "coords": "X: 15288, Z: -11719",
            "allies": "ЕС, Петрозаводск, Balashow, Велики китай",
            "enemies": "СССР",
            "tasks": "1. Перестроить магаз, пополнить каз. \n2. Набрать игроков. \n3. Основаться на территориях.",
            "jobs": {
                "miner": {"name": "Шахтер", "salary": "2$/стак", "slots": 5, "taken": 0, "desc": "Добывайте железную руду (блоками). С вами свяжется мэр по поводу вашей работы."},
                "les": {"name": "Дровосек", "salary": "1.5$/стак", "slots": 5, "taken": 0, "desc": "Рубить дуб и сажать обратно. С вами свяжется мэр по поводу вашей работы."}
            },
            "shops": [
                {"name": "Скупка", "coords": "X: 15277, Z: -11720"}
            ]
        },
       "city2": {
            "name": "Великий китай",
            "owner_id": 8034060633,
            "coords": "X: 24713, Z: -6744",
            "allies": "Стальгорнскiй Ординатъ",
            "enemies": "Oxland",
            "tasks": "1. Соединить китай. \n2. Построить великую империю. \n3. Помогать нуждающимся",
            "jobs": {
                 "miner": {"name": "Шахтер", "salary": "?", "slots": 9999, "taken": 0, "desc": "Добывать булыжник. С вами свяжется мэр по поводу вашей работы."},
		"les": {"name": "Дровосек", "salary": "?", "slots": 9999, "taken": 0, "desc": "Рубить дерево. С вами свяжется мэр по поводу вашей работы."}
            },
            "shops": [
		{"name": "t spawn Великий Китай", "coords": "X: 24713, Z: -6744"}
	]
        },
        "city3": {
            "name": "Italian Imperi",
            "owner_id": ADMIN_ID,
            "coords": "X: ?, Z: ?", 
            "allies": "ЕС, Монолит, Бразил, SPQR",
            "enemies": "СССР",
            "tasks": "Стройка площади города, первых ЖК",
            "jobs": {
                "miner": {"name": "Шахтер", "salary": "Договорная", "slots": 9999, "taken": 0, "desc": "Копать ресурсы."},
                "les": {"name": "Дровосек", "salary": "Договорная", "slots": 9999, "taken": 0, "desc": "Рубить дерево."},
                "pve": {"name": "ПВЕ", "salary": "50$ за работу", "slots": 9999, "taken": 0, "desc": "ХЗ"}
            },
            "shops": []
        },
        "city4": {
            "name": "Петрозаводск",
            "owner_id": 8403214958,
            "coords": "X: 7159, Z: -12741",
            "allies": "Нет",
            "enemies": "Карелия",
            "tasks": "Стать самым сильным городом в Карелии",
            "jobs": {
                "englishJob": {"name": "Лесоруб", "salary": "0.5$", "slots": 9999, "taken": 0, "desc": "Рубить деревья. С вами свяжется мэр по поводу вашей работы."}
            },
            "shops": []
        },
        "city5": {
            "name": "Сидней",
            "owner_id": 2067175078,
            "coords": "X: 34400, Z: 9487",
            "allies": "Шотландия",
            "enemies": "Нет",
            "tasks": "Всестороннее экономическое развитие",
            "jobs": {
                "englishJob": {"name": "Фермер", "salary": "2$ в час + премии", "slots": 9999, "taken": 0, "desc": "С вами свяжется мэр по поводу вашей работы."}
            },
            "shops": []
        },
        "city6": {
            "name": "Крипероленд",
            "owner_id": 1887102690,
            "coords": "X: -11525, Z: 954",
            "allies": "Нация",
            "enemies": "Нет",
            "tasks": "1. Развить город, прокачать максимальный век\n2. Найти много людей в город\n3. Накопить владельцу на донат",
            "jobs": {
                "englishjob": {"name": "?", "salary": "?$", "slots": 9999, "taken": 0, "desc": "С вами свяжется мэр по поводу вашей работы."}
            },
            "shops": [
                {"name": "Магаз", "coords": "X: -11527, Z: 960"}
            ]
        },
        "city7": {
            "name": "Brazill",
            "owner_id": 8508825631,
            "coords": "X: 13289, Z: 2148",
            "allies": "Хумаита-Дистрикт, Япония",
            "enemies": "Нет",
            "tasks": "НАШ ГОРОД = ГОРОД ПОСТАВЩИК ДЕРЕВА! ИЩЕМ ДОСТОЙНЫХ ЛЮДЕЙ ДЛЯ ФАРМА, ЗАРПЛАТА БУДЕТ ЗАВИСИТЬ ОТ КОЛ-ВА СТАКОВ! ПИСАТЬ В ТГ @gamevea МЫ ИСКАЛИ ИМЕННО ТЕБЯ!!",
            "jobs": {
                "englishjob": {"name": "Лесоруб", "salary": "Зависит от выполненной работы", "slots": 2, "taken": 0, "desc": "С вами свяжется мэр по поводу вашей работы."},
                "miner": {"name": "Шахтер", "salary": "Зависит от выполненной работы", "slots": 2, "taken": 0, "desc": "С вами свяжется мэр по поводу вашей работы."},
                "builder": {"name": "Строитель", "salary": "Зависит от выполненной работы", "slots": 2, "taken": 0, "desc": "С вами свяжется мэр по поводу вашей работы."},
                "pve": {"name": "Военнослужащий", "salary": "Зависит от выполненной работы", "slots": 2, "taken": 0, "desc": "С вами свяжется мэр по поводу вашей работы."}
            },
            "shops": []
        },
	"city8": {
            "name": "Джакарта",
            "owner_id": 8057012319,
            "coords": "X: , Z: ",
            "allies": "Хроноград, Муром, Токио",
            "enemies": "Монолит, Византия",
            "tasks": "1. Забрать чд. \n2. Отстроить город и жить",
            "jobs": {
                "miner": {"name": "Шахтер", "salary": "5$ за 64 железа, 15$ за 64 алмазов", "slots": 9999, "taken": 0, "desc": "Копать ресурсы. С вами свяжется мэр по поводу вашей работы."},
                "les": {"name": "Дровосек", "salary": "2-3$ за 64 дуба", "slots": 9999, "taken": 0, "desc": "Рубить дуб. С вами свяжется мэр по поводу вашей работы."},
                "pve": {"name": "Фармер", "salary": "4-10$ за 64 пороха", "slots": 9999, "taken": 0, "desc": "С вами свяжется мэр по поводу вашей работы."}
            },
            "shops": [
                {"name": "Ашан", "coords": "X: -200, Z: -5255"},
		{"name": "ShopProkyber", "coords": "X: 16352, Z: -8826"},
		{"name": "Магнит", "coords": "X: 23285, Z: 1427"}
            ]
        },
	"city9": {
            "name": "Оренбург",
            "owner_id": 5172023955,
            "coords": "X: 11300, Z: -10700",
            "allies": "Нет",
            "enemies": "Асуньсон, Тамбов",
            "tasks": "Контролировать Урал и пред уралье",
            "jobs": {
                "les": {"name": "Лесоруб", "salary": "?", "slots": 9999, "taken": 0, "desc": "Рубить деревья. С вами свяжется мэр по поводу вашей работы."}
            },
            "shops": []
        },
	"city10": {
            "name": "Bernad Imperia",
            "owner_id": 7730560352,
            "coords": "X: 2345, Z: -9955",
            "allies": "Бернад, Гамбург, Реф-Ера, вассал Каменногорск, Германия, Византия, Крепорлоид",
            "enemies": "Paris, Прага, Советская Бавария",
            "tasks": "1. ",
            "jobs": {
                "englishjob": {"name": "работа", "salary": "зп$", "slots": 9999, "taken": 0, "desc": "задача. С вами свяжется мэр по поводу вашей работы."}
            },
            "shops": [
                {"name": "Скупка", "coords": "X: , Z: "}
            ]
        },
	"city11": {
            "name": "Германия",
            "owner_id": 5871381882,
            "coords": "X: ?, Z: ?",
            "allies": "Paris, нация The German Empire",
            "enemies": "Хроноград, Англия",
            "tasks": "Развитие нации на топ 1",
            "jobs": {
                "englishjob": {"name": "Строитель", "salary": "?", "slots": 9999, "taken": 0, "desc": "С вами свяжется мэр по поводу вашей работы."},
		"les": {"name": "Шахтер", "salary": "?", "slots": 9999, "taken": 0, "desc": "С вами свяжется мэр по поводу вашей работы."},
                "pve": {"name": "Фермер", "salary": "?", "slots": 9999, "taken": 0, "desc": "С вами свяжется мэр по поводу вашей работы."}

            },
            "shops": [
                {"name": "Золотая Залупа", "coords": "X: ?, Z: ?"}
            ]
        }
    },
    "users_jobs": {},  
    "all_users": [] 
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
            # Проверка целостности
            updated = False
            for city_code, city_data in db["cities"].items():
                if "owner_id" not in city_data:
                    city_data["owner_id"] = ADMIN_ID
                    updated = True
                if "shops" not in city_data:
                    city_data["shops"] = []
                    updated = True
            if updated:
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

# --- ФУНКЦИЯ ОТЛОЖЕННОГО УВЕДОМЛЕНИЯ О РАБОТЕ ---
async def notify_owner_delayed(user_id, user_full_name, user_username, city_name, job_name, owner_id):
    try:
        # Ждем 300 секунд (5 минут)
        await asyncio.sleep(300) 
        
        # Формируем ссылку на профиль
        user_link = f"<a href='tg://user?id={user_id}'>{user_full_name}</a>"
        username_text = f"@{user_username}" if user_username else "Нет юзернейма"
        
        text = (
            f"🔔 <b>Уведомление для владельца г. {city_name}</b>\n\n"
            f"👤 Игрок: {user_link}\n"
            f"🔖 Юзернейм: {username_text}\n"
            f"🔨 Взял работу: <b>{job_name}</b>\n"
            f"⏳ Прошло 5 минут, он всё еще работает.\n\n"
            f"📝 <i>Напишите ему для инструктажа.</i>"
        )
        await bot.send_message(owner_id, text, parse_mode="HTML")
        
    except asyncio.CancelledError:
        logging.info(f"Уведомление для {user_id} отменено (уволился).")
    except Exception as e:
        logging.error(f"Ошибка отправки владельцу: {e}")
    finally:
        if user_id in pending_notifications:
            del pending_notifications[user_id]

# --- ИНИЦИАЛИЗАЦИЯ ---
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Состояния
class Form(StatesGroup):
    waiting_for_application = State()  # Заявка на город
    waiting_for_join_request = State() # Заявка на вступление

# --- КЛАВИАТУРЫ ---
def get_main_menu():
    buttons = [
        [InlineKeyboardButton(text="🏪 Список магазинов", callback_data="menu_shops")],
        [InlineKeyboardButton(text="🏙 Список городов", callback_data="menu_cities")],
        [InlineKeyboardButton(text="📝 Отправить заявку на добавление города/Техподдержка", callback_data="menu_apply")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_cities_keyboard(action_prefix="city"):
    buttons = []
    for code, data in db["cities"].items():
        buttons.append([InlineKeyboardButton(text=data["name"], callback_data=f"{action_prefix}_{code}")])
    buttons.append([InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_city_menu_keyboard(city_code, user_id=None):
    buttons = [
        [InlineKeyboardButton(text="🙋‍♂️ Хочу вступить", callback_data=f"join_{city_code}")],
        [InlineKeyboardButton(text="💼 Работы", callback_data=f"jobs_{city_code}")],
        [InlineKeyboardButton(text="🏪 Магазины", callback_data=f"showshops_{city_code}")],
        [InlineKeyboardButton(text="🤝 Союзники", callback_data=f"allies_{city_code}")],
        [InlineKeyboardButton(text="⚔️ Враги", callback_data=f"enemies_{city_code}")],
        [InlineKeyboardButton(text="📍 Координаты", callback_data=f"coords_{city_code}")],
        [InlineKeyboardButton(text="📜 Задачи", callback_data=f"tasks_{city_code}")],
    ]
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
        f"👋 Привет! Здесь ты можешь найти работу, город или найти работников и жетелей в свой город на Аврелии ХХ!\nДобро пожаловать в меню.", 
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "main_menu")
async def back_to_main(callback: CallbackQuery):
    await callback.message.edit_text("Выбери действие:", reply_markup=get_main_menu())

# --- ХЕНДЛЕРЫ: ПРОСМОТР ---
@dp.callback_query(F.data == "menu_shops")
async def menu_shops_list(callback: CallbackQuery):
    await callback.message.edit_text(
        "🏪 <b>Список магазинов</b>\nВыберите город:",
        reply_markup=get_cities_keyboard(action_prefix="shoplist"),
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("shoplist_"))
async def show_shops_in_city(callback: CallbackQuery):
    city_code = callback.data.split("_")[1]
    city = db["cities"][city_code]
    shops = city.get("shops", [])
    text = f"🏪 <b>Магазины в г. {city['name']}</b>:\n\n"
    if not shops:
        text += "В этом городе пока нет магазинов."
    else:
        for shop in shops:
            text += f"🛒 <b>{shop['name']}</b>\n📍 <code>{shop['coords']}</code>\n\n"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 К выбору города", callback_data="menu_shops")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data.startswith("showshops_"))
async def show_shops_internal(callback: CallbackQuery):
    city_code = callback.data.split("_")[1]
    city = db["cities"][city_code]
    shops = city.get("shops", [])
    text = f"🏪 <b>Магазины в г. {city['name']}</b>:\n\n"
    if not shops:
        text += "В этом городе пока нет магазинов."
    else:
        for shop in shops:
            text += f"🛒 <b>{shop['name']}</b>\n📍 <code>{shop['coords']}</code>\n\n"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад в город", callback_data=f"city_{city_code}")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data == "menu_cities")
async def menu_cities_list(callback: CallbackQuery):
    await callback.message.edit_text(
        "🏙 <b>Список городов</b>\nВыберите город:", 
        reply_markup=get_cities_keyboard(action_prefix="city"),
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("city_"))
async def show_city_menu(callback: CallbackQuery):
    city_code = callback.data.split("_")[1]
    city_name = db["cities"][city_code]["name"]
    user_id = callback.from_user.id
    text = f"🏙 <b>Город: {city_name}</b>\nВыберите раздел:"
    await callback.message.edit_text(text, reply_markup=get_city_menu_keyboard(city_code, user_id), parse_mode="HTML")

@dp.callback_query(F.data.startswith(("allies_", "enemies_", "coords_", "tasks_")))
async def show_info(callback: CallbackQuery):
    parts = callback.data.split("_", 1)
    action = parts[0]
    city_code = parts[1]
    city_data = db["cities"][city_code]
    info_map = {
        "allies": f"🤝 <b>Союзники:</b>\n{city_data['allies']}",
        "enemies": f"⚔️ <b>Враги:</b>\n{city_data['enemies']}",
        "coords": f"📍 <b>Координаты спавна:</b>\n<code>{city_data['coords']}</code>",
        "tasks": f"📜 <b>Задачи города:</b>\n{city_data['tasks']}"
    }
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data=f"city_{city_code}")]])
    await callback.message.edit_text(info_map[action], reply_markup=back_kb, parse_mode="HTML")

# --- ЗАЯВКА НА ДОБАВЛЕНИЕ ГОРОДА (АДМИНУ) ---
@dp.callback_query(F.data == "menu_apply")
async def start_application(callback: CallbackQuery, state: FSMContext):
    # Используем тройные кавычки, чтобы не было ошибок переноса
    text = """📝 <b>Заявка на добавление города</b>

Напишите одним сообщением:
1. Название
2. Координаты спавна
3. Союзники
4. Враги
5. Задачи города
6. Работы, зп и свободные места
7. Магазины и его координаты, если есть

Напишите 'отмена', чтобы вернуться."""
    await callback.message.edit_text(text, parse_mode="HTML")
    await state.set_state(Form.waiting_for_application)

@dp.message(Form.waiting_for_application)
async def process_application(message: Message, state: FSMContext):
    if message.text.lower() == 'отмена':
        await state.clear()
        await message.answer("Заявка отменена.", reply_markup=get_main_menu())
        return
    application_text = message.text
    user = message.from_user
    safe_name = html.escape(user.full_name)
    safe_username = html.escape(str(user.username)) if user.username else "Нет юзернейма"
    safe_text = html.escape(application_text)
    
    user_link = f"<a href='tg://user?id={user.id}'>{safe_name}</a>"
    
    admin_msg = (
        f"📩 <b>НОВАЯ ЗАЯВКА НА ГОРОД!</b>\n\n"
        f"👤 От: {user_link} (@{safe_username})\n"
        f"🆔 ID: <code>{user.id}</code>\n\n"
        f"📄 <b>Текст:</b>\n{safe_text}"
    )
    try:
        await bot.send_message(ADMIN_ID, admin_msg, parse_mode="HTML")
        await message.answer("✅ <b>Заявка успешно отправлена!</b>", reply_markup=get_main_menu(), parse_mode="HTML")
    except Exception as e:
        await message.answer(f"Ошибка отправки: {e}", reply_markup=get_main_menu())
    await state.clear()

# --- ЗАЯВКА НА ВСТУПЛЕНИЕ В ГОРОД (МЭРУ) ---
@dp.callback_query(F.data.startswith("join_"))
async def start_join_request(callback: CallbackQuery, state: FSMContext):
    city_code = callback.data.split("_")[1]
    city_name = db["cities"][city_code]["name"]
    
    await state.update_data(city_code=city_code)
    
    # Тройные кавычки (f-string) - самое надежное решение
    text = f"""🙋‍♂️ <b>Вступление в город: {city_name}</b>

Напишите небольшую анкету одним сообщением (например):
- Ваш ник в игре
- Что вы умеете
- Почему хотите к нам?
- Ваша краткая история (по желанию)

Ваша заявка улетит лично Мэру города.

Напишите 'отмена', чтобы вернуться."""
    
    await callback.message.edit_text(text, parse_mode="HTML")
    await state.set_state(Form.waiting_for_join_request)

@dp.message(Form.waiting_for_join_request)
async def process_join_request(message: Message, state: FSMContext):
    # --- ВОТ ЗДЕСЬ ДОБАВЛЕНА ПРОВЕРКА НА ОТМЕНУ ---
    if message.text.lower() == 'отмена':
        await state.clear()
        await message.answer("Заявка отменена.", reply_markup=get_main_menu())
        return
        
    data = await state.get_data()
    city_code = data.get("city_code")
    
    if not city_code or city_code not in db["cities"]:
        await message.answer("Ошибка: Город не найден. Начните заново.", reply_markup=get_main_menu())
        await state.clear()
        return

    city = db["cities"][city_code]
    owner_id = city.get("owner_id", ADMIN_ID)
    
    user = message.from_user
    safe_name = html.escape(user.full_name)
    safe_username = html.escape(str(user.username)) if user.username else "Нет юзернейма"
    safe_text = html.escape(message.text)
    
    user_link = f"<a href='tg://user?id={user.id}'>{safe_name}</a>"
    
    mayor_msg = (
        f"📬 <b>ЗАЯВКА НА ВСТУПЛЕНИЕ!</b>\n"
        f"Город: <b>{city['name']}</b>\n\n"
        f"👤 От: {user_link}\n"
        f"🔖 Юзернейм: @{safe_username}\n\n"
        f"📝 <b>Анкета:</b>\n{safe_text}\n\n"
        f"<i>Нажмите на имя или юзернейм, чтобы ответить.</i>"
    )
    
    try:
        await bot.send_message(owner_id, mayor_msg, parse_mode="HTML")
        await message.answer(f"✅ <b>Заявка отправлена мэру города {city['name']}!</b>\nЖдите ответа в ЛС.", reply_markup=get_main_menu(), parse_mode="HTML")
    except Exception as e:
        logging.error(f"Не удалось отправить мэру: {e}")
        await message.answer("Ошибка отправки (возможно, у мэра закрыта личка).", reply_markup=get_main_menu())
    
    await state.clear()

# --- РАБОТА И УВЕДОМЛЕНИЯ ---
@dp.callback_query(F.data.startswith("jobs_"))
async def show_jobs(callback: CallbackQuery):
    city_code = callback.data.split("_")[1]
    user_id = callback.from_user.id
    text = "💼 <b>Биржа труда</b>\nНажмите на вакансию:"
    await callback.message.edit_text(text, reply_markup=get_jobs_keyboard(city_code, user_id), parse_mode="HTML")

@dp.callback_query(F.data.startswith("takejob_"))
async def take_job(callback: CallbackQuery):
    parts = callback.data.split("_")
    city_code = parts[1]
    job_code = parts[2]
    user_id = callback.from_user.id
    str_user_id = str(user_id)
    
    if str_user_id in db["users_jobs"]:
        await callback.answer("Вы уже работаете!", show_alert=True)
        return
    
    city = db["cities"][city_code]
    job_info = city["jobs"][job_code]
    if job_info["taken"] >= job_info["slots"]:
        await callback.answer("Места закончились!", show_alert=True)
        return

    # Запись в БД
    job_info["taken"] += 1
    db["users_jobs"][str_user_id] = {"city_code": city_code, "job_code": job_code}
    save_db()
    
    owner_id = city.get("owner_id")
    if owner_id:
        user = callback.from_user
        full_name = html.escape(user.full_name)
        username = user.username
        
        task = asyncio.create_task(
            notify_owner_delayed(user_id, full_name, username, city["name"], job_info["name"], owner_id)
        )
        pending_notifications[user_id] = task
    
    congrats_text = (
        f"🎉 <b>Поздравляю!</b>\n"
        f"Должность: <b>{job_info['name']}</b>\n"
        f"Зарплата: {job_info['salary']}\n\n"
        f"📝 <b>Обязанности:</b>\n{job_info['desc']}"
    )
    await callback.message.edit_text(congrats_text, reply_markup=get_jobs_keyboard(city_code, user_id), parse_mode="HTML")

@dp.callback_query(F.data.startswith("quitjob_"))
async def quit_job(callback: CallbackQuery):
    city_code = callback.data.split("_")[1]
    user_id = callback.from_user.id
    str_user_id = str(user_id)
    
    if str_user_id not in db["users_jobs"]:
        await callback.answer("Вы не работаете!", show_alert=True)
        return
    
    user_job = db["users_jobs"][str_user_id]
    job_code = user_job["job_code"]
    job_info = db["cities"][city_code]["jobs"][job_code]
    job_info["taken"] -= 1
    del db["users_jobs"][str_user_id]
    save_db()
    
    if user_id in pending_notifications:
        pending_notifications[user_id].cancel()
        del pending_notifications[user_id]
    
    await callback.answer("Вы уволились!", show_alert=True)
    city_name = db["cities"][city_code]["name"]
    text = f"🏙 <b>Город: {city_name}</b>\nВыберите раздел:"
    await callback.message.edit_text(text, reply_markup=get_city_menu_keyboard(city_code, user_id), parse_mode="HTML")

@dp.callback_query(F.data == "ignore")
async def ignore_click(callback: CallbackQuery):
    await callback.answer("Эта вакансия недоступна!")

# --- РАССЫЛКА ---
@dp.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer(f"⛔ Нет прав. Ваш ID: {message.from_user.id}")
        return
    text = message.text.replace('/broadcast', '').strip()
    if not text:
        await message.answer("⚠️ Вы не ввели текст.")
        return
    users = db.get("all_users", [])
    if not users:
        add_user_to_db(message.from_user.id)
        users = db.get("all_users", [])
        await message.answer("⚠️ База пуста.")
        return
    await message.answer(f"📢 Рассылка на {len(users)} чел...")
    success = 0
    errors = 0
    for user_id in users:
        try:
            await bot.send_message(user_id, text)
            success += 1
            await asyncio.sleep(0.05)
        except Exception:
            errors += 1
    await message.answer(f"🏁 Рассылка: ✅ {success}, ❌ {errors}")

# --- ФОНОВАЯ ЗАДАЧА ---
async def broadcaster():
    while True:
        await asyncio.sleep(AD_INTERVAL)
        users = db.get("all_users", [])
        if not users:
            continue
        for user_id in users:
            try:
                await bot.send_message(user_id, AD_TEXT)
                await asyncio.sleep(0.05)
            except Exception:
                pass

# --- ЗАПУСК ---
async def main():
    load_db()
    print("Бот запущен...")
    asyncio.create_task(broadcaster())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())