import asyncio
import logging
import json
import os
import html
import time
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# --- КОНФИГУРАЦИЯ ---
TOKEN = "8226548122:AAHdyihHKdrXHZr4W8oFuxtNaY8tQriG4RE"
ADMIN_ID = 6131249570
AD_INTERVAL = 777600  #
REMINDER_INTERVAL = 43200 # 12 часов
AD_TEXT = "Мой Ютуб: https://youtube.com/@megakruiiiutel?si=EwNMi2obVaqA_hJs. Если вы хотите подобную рекламу своего города/магаза в боте, пишите: @megakruiii"
DB_FILE = "database.json"

# --- ЛОГИРОВАНИЕ ---
logging.basicConfig(level=logging.INFO)

# --- ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ---
pending_notifications = {}

# --- БАЗА ДАННЫХ ---
default_db = {
    "cities": {
        "city1": {
            "name": "Стальгорнскiй Ординатъ",
            "owner_id": 6131249570,
            "coords": "X: 15288, Z: -11719",
            "allies": "ЕС, Петрозаводск, Balashow, Великий китай, Ягодники",
            "enemies": "СССР",
            "tasks": "1. Перестроить магаз и каз. \n2. Набрать игроков. \n3. Основаться на территориях.",
            "jobs": {
                "miner": {"name": "Шахтер", "salary": "10$", "slots": 5, "taken": 0, "desc": "Добывайте железную руду (блоками). С вами свяжется мэр по поводу вашей работы."},
                "les": {"name": "Дровосек", "salary": "1.5$", "slots": 5, "taken": 0, "desc": "Рубить дуб и сажать обратно. С вами свяжется мэр по поводу вашей работы."}
            },
            "shops": [{"name": "Скупка", "coords": "X: 15277, Z: -11720"}]
        },
        "city2": {
            "name": "Великий китай",
            "owner_id": 8034060633,
            "coords": "X: 24713, Z: -6744",
            "allies": "Стальгорнскiй Ординатъ",
            "enemies": "Oxland",
            "tasks": "1. Соединить китай. \n2. Построить великую империю. \n3. Помогать нуждающимся",
            "jobs": {
                "miner": {"name": "Шахтер", "salary": "0", "slots": 50, "taken": 0, "desc": "Добывать булыжник. С вами свяжется мэр по поводу вашей работы."},
                "les": {"name": "Дровосек", "salary": "0", "slots": 50, "taken": 0, "desc": "Рубить дерево. С вами свяжется мэр по поводу вашей работы."}
            },
            "shops": [{"name": "t spawn Великий Китай", "coords": "X: 24713, Z: -6744"}]
        },
        "city3": {
            "name": "Italian Imperi",
            "owner_id": 6131249570,
            "coords": "X: ?, Z: ?", 
            "allies": "ЕС, Монолит, Бразил, SPQR",
            "enemies": "СССР",
            "tasks": "Стройка площади города, первых ЖК",
            "jobs": {
                "miner": {"name": "Шахтер", "salary": "0", "slots": 1, "taken": 0, "desc": "Копать ресурсы."},
                "les": {"name": "Дровосек", "salary": "0", "slots": 1, "taken": 0, "desc": "Рубить дерево."},
                "pve": {"name": "ПВЕ", "salary": "50$", "slots": 1, "taken": 0, "desc": "ХЗ"}
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
                "englishJob": {"name": "Лесоруб", "salary": "0.5$", "slots": 50, "taken": 0, "desc": "Рубить деревья. С вами свяжется мэр по поводу вашей работы."}
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
                "englishJob": {"name": "Фермер", "salary": "2$", "slots": 50, "taken": 0, "desc": "Фармить. С вами свяжется мэр по поводу вашей работы."}
            },
            "shops": []
        },
        "city6": {
            "name": "Крипероленд",
            "owner_id": 1887102690,
            "coords": "X: -11525, Z: 954",
            "allies": "Нация",
            "enemies": "Нет",
            "tasks": "1. Развить город\n2. Найти людей\n3. Накопить на донат",
            "jobs": {
                "englishjob": {"name": "?", "salary": "?$", "slots": 50, "taken": 0, "desc": "Разнорабочий. С вами свяжется мэр по поводу вашей работы."}
            },
            "shops": [{"name": "Магаз", "coords": "X: -11527, Z: 960"}]
        },
        "city7": {
            "name": "Brazill",
            "owner_id": 8508825631,
            "coords": "X: 13289, Z: 2148",
            "allies": "Хумаита-Дистрикт, Япония",
            "enemies": "Нет",
            "tasks": "ГОРОД ПОСТАВЩИК ДЕРЕВА!",
            "jobs": {
                "englishjob": {"name": "Лесоруб", "salary": "Сдельная", "slots": 2, "taken": 0, "desc": "Рубить лес. С вами свяжется мэр по поводу вашей работы."},
                "miner": {"name": "Шахтер", "salary": "Сдельная", "slots": 2, "taken": 0, "desc": "Копать шахту. С вами свяжется мэр по поводу вашей работы."},
                "builder": {"name": "Строитель", "salary": "Сдельная", "slots": 2, "taken": 0, "desc": "Строить. С вами свяжется мэр по поводу вашей работы."},
                "pve": {"name": "Военнослужащий", "salary": "Сдельная", "slots": 2, "taken": 0, "desc": "Служить. С вами свяжется мэр по поводу вашей работы."}
            },
            "shops": []
        },
        "city8": {
            "name": "Джакарта",
            "owner_id": 8057012319,
            "coords": "X: 0, Z: 0",
            "allies": "Хроноград, Муром, Токио",
            "enemies": "Монолит, Византия",
            "tasks": "1. Забрать чд. \n2. Отстроить город",
            "jobs": {
                "miner": {"name": "Шахтер", "salary": "5$", "slots": 50, "taken": 0, "desc": "Копать железо. С вами свяжется мэр по поводу вашей работы."},
                "les": {"name": "Дровосек", "salary": "3$", "slots": 50, "taken": 0, "desc": "Рубить дуб. С вами свяжется мэр по поводу вашей работы."},
                "pve": {"name": "Фармер", "salary": "10$", "slots": 50, "taken": 0, "desc": "Фармить порох. С вами свяжется мэр по поводу вашей работы."}
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
            "tasks": "Контролировать Урал",
            "jobs": {
                "les": {"name": "Лесоруб", "salary": "?", "slots": 50, "taken": 0, "desc": "Рубить деревья. С вами свяжется мэр по поводу вашей работы."}
            },
            "shops": []
        },
        "city10": {
            "name": "Bernad Imperia",
            "owner_id": 7730560352,
            "coords": "X: 2345, Z: -9955",
            "allies": "Бернад, Гамбург, Германия",
            "enemies": "Paris, Прага",
            "tasks": "Развитие",
            "jobs": {
                "englishjob": {"name": "Разнорабочий", "salary": "Договорная", "slots": 50, "taken": 0, "desc": "Выполнение поручений. С вами свяжется мэр по поводу вашей работы."}
            },
            "shops": []
        },
        "city11": {
            "name": "Германия",
            "owner_id": 5871381882,
            "coords": "X: ?, Z: ?",
            "allies": "Paris, German Empire",
            "enemies": "Хроноград, Англия",
            "tasks": "Топ 1",
            "jobs": {
                "englishjob": {"name": "Строитель", "salary": "?", "slots": 50, "taken": 0, "desc": "Строить. С вами свяжется мэр по поводу вашей работы."},
                "les": {"name": "Шахтер", "salary": "?", "slots": 50, "taken": 0, "desc": "Копать. С вами свяжется мэр по поводу вашей работы."},
                "pve": {"name": "Фермер", "salary": "?", "slots": 50, "taken": 0, "desc": "Фармить. С вами свяжется мэр по поводу вашей работы."}
            },
            "shops": [{"name": "Золотая Залупа", "coords": "X: ?, Z: ?"}]
        }
    },
    "users_jobs": {},
    "all_users": [
       	5168622042,
	8538038923,
	6107282284,
	8056310759,
	6044305371,
	1203611337,
	1682016615,
	1968109248,
	5333551908,
	5982379827,
	1887102690,
	8403214958,
	2067175078,
	7371804797,
	5911967895,
	8508825631,
	6192464727,
	8034060633,
	5484811545,
	6096509532,
	8057012319,
        5172023955,
        6603459440,
        8112186870,
        1377005437,
        6602569186,
        6760121798,
        5871381882,
        5701585720,
        7597022964,
        7730560352,
        7002263379,
	5697862494,
        6238840057,
	6015333885,
	1701320721,
        1105094962,
        7611945178,
        5219075653,
        8142832883,
        5214578781,
        6131249570,
        6550764700,
        5062106501,
        1985082513,
        6330640330,
        5330947864,
        1774039816,
	7590496280,
        8344804354,
        6789816316,
        6053325505,
        7671924160,
        6301635399,
        1087968824,
        7032660827,
        8542988136
    ],
    "active_alliances": [],
    "pending_rewards": []
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
            
            updated = False
            if "active_alliances" not in db:
                db["active_alliances"] = []
                updated = True
            if "pending_rewards" not in db:
                db["pending_rewards"] = []
                updated = True
                
            for k, v in default_db["cities"].items():
                if k not in db["cities"]:
                    db["cities"][k] = v
                    updated = True
                else:
                    if "owner_id" not in db["cities"][k]:
                        db["cities"][k]["owner_id"] = v["owner_id"]
                        updated = True
                    # ИСПРАВЛЕНИЕ СЛОТОВ:
                    # Проходим по всем работам и если видим 9999, меняем на 50
                    if "jobs" in db["cities"][k]:
                        for job_key, job_data in db["cities"][k]["jobs"].items():
                            if job_data.get("slots") == 9999:
                                job_data["slots"] = 50
                                updated = True

            code_users = set(default_db["all_users"])
            file_users = set(db.get("all_users", []))
            if len(code_users) > len(file_users):
                db["all_users"] = list(code_users.union(file_users))
                updated = True

            if updated:
                save_db()
                logging.info("БД обновлена: слоты поправлены на 50.")
        except Exception as e:
            logging.error(f"Ошибка загрузки БД: {e}")
            db = default_db

def save_db():
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Ошибка сохранения БД: {e}")

# --- ФУНКЦИИ ---
async def notify_owner_delayed(user_id, user_full_name, user_username, city_name, job_name, owner_id):
    try:
        await asyncio.sleep(300) 
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
        pass
    except Exception as e:
        logging.error(f"Ошибка отправки владельцу: {e}")
    finally:
        if user_id in pending_notifications:
            del pending_notifications[user_id]

def get_owned_city(user_id):
    """Возвращает код города, которым владеет пользователь, или None"""
    for code, city in db["cities"].items():
        if city.get("owner_id") == user_id:
            return code
    return None

# --- ИНИЦИАЛИЗАЦИЯ ---
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Состояния
class Form(StatesGroup):
    waiting_for_application = State()
    waiting_for_join_request = State()
    waiting_for_idea = State()

class AllianceForm(StatesGroup):
    waiting_for_type = State()
    waiting_for_against = State()

# --- КЛАВИАТУРЫ ---
def get_main_menu():
    buttons = [
        [InlineKeyboardButton(text="💡 Предложить идею", callback_data="menu_idea")],
        [InlineKeyboardButton(text="🤝 Союзы", callback_data="menu_alliances")],
        [InlineKeyboardButton(text="🏪 Список магазинов", callback_data="menu_shops")],
        [InlineKeyboardButton(text="🏙 Список городов", callback_data="menu_cities")],
        [InlineKeyboardButton(text="📝 Заявка на город / Техподдержка", callback_data="menu_apply")]
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
    
    user_owned_city = get_owned_city(user_id)
    if user_owned_city and user_owned_city != city_code:
        buttons.append([InlineKeyboardButton(text="🕊 Заключить союз", callback_data=f"diplomacy_{city_code}")])

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

# --- ХЕНДЛЕРЫ ---
@dp.message(Command("start"))
async def cmd_start(message: Message):
    add_user_to_db(message.from_user.id)
    await message.answer(
        f"👋 Привет! Добро пожаловать в меню.", 
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "main_menu")
async def back_to_main(callback: CallbackQuery):
    await callback.message.edit_text("Выбери действие:", reply_markup=get_main_menu())

# --- ХЕНДЛЕРЫ: ИДЕИ ---
@dp.callback_query(F.data == "menu_idea")
async def start_idea(callback: CallbackQuery, state: FSMContext):
    text = (
        "💡 **Предложить идею для видео**\n\n"
        "Напишите вашу идею. Если она будет реализована, вы получите награду (монеты)!\n"
        "Напишите 'отмена', чтобы вернуться."
    )
    await callback.message.edit_text(text, parse_mode="Markdown")
    await state.set_state(Form.waiting_for_idea)

@dp.message(Form.waiting_for_idea)
async def process_idea(message: Message, state: FSMContext):
    if message.text.lower() == 'отмена':
        await state.clear()
        await message.answer("Отменено.", reply_markup=get_main_menu())
        return

    idea_text = message.text
    user = message.from_user
    safe_name = html.escape(user.full_name)
    user_link = f"<a href='tg://user?id={user.id}'>{safe_name}</a>"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👍 Понравилось (Напомнить)", callback_data=f"idea_like_{user.id}")],
        [InlineKeyboardButton(text="👎 Не понравилось", callback_data="idea_dislike")]
    ])

    admin_msg = (
        f"💡 <b>НОВАЯ ИДЕЯ ОТ ПОДПИСЧИКА!</b>\n\n"
        f"👤 От: {user_link}\n"
        f"🆔 ID: <code>{user.id}</code>\n\n"
        f"📜 <b>Суть:</b>\n{html.escape(idea_text)}"
    )

    try:
        await bot.send_message(ADMIN_ID, admin_msg, reply_markup=kb, parse_mode="HTML")
        await message.answer("✅ Ваша идея отправлена администратору!", reply_markup=get_main_menu())
    except Exception as e:
        await message.answer("Ошибка отправки.", reply_markup=get_main_menu())
    
    await state.clear()

@dp.callback_query(F.data == "idea_dislike")
async def idea_dislike(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer("Идея отклонена.")

@dp.callback_query(F.data.startswith("idea_like_"))
async def idea_like(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[2])
    
    reward_entry = {
        "user_id": user_id,
        "timestamp": time.time(),
    }
    db["pending_rewards"].append(reward_entry)
    save_db()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Выслал монеты", callback_data=f"idea_sent_{user_id}")]
    ])
    
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer("Ок! Буду напоминать.")

@dp.callback_query(F.data.startswith("idea_sent_"))
async def idea_sent(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[2])
    
    db["pending_rewards"] = [item for item in db["pending_rewards"] if item["user_id"] != user_id]
    save_db()

    await callback.message.delete()
    await callback.answer("Награда подтверждена.")
    
    try:
        await bot.send_message(user_id, "🎉 <b>Поздравляем!</b>\nВаша идея понравилась администратору, вам зачислены монеты!", parse_mode="HTML")
    except: pass

# --- ХЕНДЛЕРЫ: ДИПЛОМАТИЯ ---
@dp.callback_query(F.data == "menu_alliances")
async def show_alliances(callback: CallbackQuery):
    alliances = db.get("active_alliances", [])
    if not alliances:
        text = "🤝 <b>Активные союзы</b>\n\nНа данный момент союзов не заключено."
    else:
        text = "🤝 <b>Активные союзы</b>\n\n"
        for al in alliances:
            c1_name = db["cities"][al["source"]]["name"]
            c2_name = db["cities"][al["target"]]["name"]
            
            against_name = "Неизвестно"
            if al["against"] in db["cities"]:
                against_name = db["cities"][al["against"]]["name"]
            elif al["against"] == "unknown":
                against_name = "Пока неизвестно"
                
            text += (
                f"🔹 <b>{c1_name}</b> + <b>{c2_name}</b>\n"
                f"Тип: {al['type']}\n"
                f"Против: <i>{against_name}</i>\n\n"
            )
            
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data.startswith("diplomacy_"))
async def start_diplomacy(callback: CallbackQuery, state: FSMContext):
    target_city_code = callback.data.split("_")[1]
    source_city_code = get_owned_city(callback.from_user.id)
    
    if not source_city_code:
        await callback.answer("Вы не являетесь мэром!", show_alert=True)
        return

    await state.update_data(target=target_city_code, source=source_city_code)
    
    buttons = [
        [InlineKeyboardButton(text="💰 Экономический", callback_data="all_type_Экономический")],
        [InlineKeyboardButton(text="⚔️ Захватнический", callback_data="all_type_Захватнический")],
        [InlineKeyboardButton(text="🛡 Оборонительный", callback_data="all_type_Оборонительный")],
        [InlineKeyboardButton(text="🌐 Все варианты", callback_data="all_type_Полный")],
        [InlineKeyboardButton(text="🔙 Отмена", callback_data="main_menu")]
    ]
    await callback.message.edit_text("Выберите тип союза:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await state.set_state(AllianceForm.waiting_for_type)

@dp.callback_query(F.data.startswith("all_type_"))
async def diplomacy_set_type(callback: CallbackQuery, state: FSMContext):
    alliance_type = callback.data.split("_")[2]
    await state.update_data(type=alliance_type)
    
    buttons = []
    data = await state.get_data()
    source = data['source']
    target = data['target']
    
    for code, city in db["cities"].items():
        if code != source and code != target:
            buttons.append([InlineKeyboardButton(text=city["name"], callback_data=f"all_against_{code}")])
            
    buttons.append([InlineKeyboardButton(text="❓ Пока неизвестно", callback_data="all_against_unknown")])
    buttons.append([InlineKeyboardButton(text="🔙 Отмена", callback_data="main_menu")])
    
    await callback.message.edit_text("Против кого этот союз?", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await state.set_state(AllianceForm.waiting_for_against)

@dp.callback_query(F.data.startswith("all_against_"))
async def diplomacy_send_request(callback: CallbackQuery, state: FSMContext):
    against_code = callback.data.replace("all_against_", "")
    data = await state.get_data()
    
    source_city = db["cities"][data['source']]
    target_city = db["cities"][data['target']]
    target_mayor_id = target_city.get("owner_id", ADMIN_ID)
    
    sender = callback.from_user
    sender_link = f"<a href='tg://user?id={sender.id}'>{html.escape(sender.full_name)}</a>"
    against_name = "Пока неизвестно"
    if against_code in db["cities"]:
        against_name = db["cities"][against_code]["name"]
        
    request_msg = (
        f"🕊 <b>ПРЕДЛОЖЕНИЕ СОЮЗА!</b>\n\n"
        f"🏙 От города: <b>{source_city['name']}</b>\n"
        f"👤 Мэр: {sender_link} (@{sender.username})\n\n"
        f"📜 Тип: <b>{data['type']}</b>\n"
        f"🎯 Против: <b>{against_name}</b>\n\n"
        f"Что будем делать?"
    )
    
    cb_data = f"{data['source']}|{data['target']}|{against_code}|{data['type']}"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Заключить", callback_data=f"al_acc|{cb_data}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"al_dec|{data['source']}")]
    ])
    
    try:
        await bot.send_message(target_mayor_id, request_msg, reply_markup=kb, parse_mode="HTML")
        await callback.message.edit_text("✅ Предложение союза отправлено! Ожидайте ответа.", reply_markup=get_main_menu())
    except Exception as e:
        await callback.message.edit_text(f"Ошибка отправки (мэр недоступен): {e}", reply_markup=get_main_menu())
    
    await state.clear()

@dp.callback_query(F.data.startswith("al_acc|"))
async def diplomacy_accept(callback: CallbackQuery):
    try:
        parts = callback.data.split("|")
        source = parts[1]
        target = parts[2]
        against = parts[3]
        atype = parts[4]
        
        new_alliance = {
            "source": source,
            "target": target,
            "against": against,
            "type": atype
        }
        db["active_alliances"].append(new_alliance)
        save_db()
        
        await callback.message.delete()
        await callback.answer("Союз заключен!")
        
        source_mayor = db["cities"][source].get("owner_id")
        target_name = db["cities"][target]["name"]
        if source_mayor:
            try:
                await bot.send_message(source_mayor, f"✅ Город <b>{target_name}</b> принял ваше предложение о союзе!", parse_mode="HTML")
            except: pass
            
    except Exception as e:
        logging.error(f"Alliance error: {e}")
        await callback.answer("Ошибка.", show_alert=True)

@dp.callback_query(F.data.startswith("al_dec|"))
async def diplomacy_decline_ask(callback: CallbackQuery):
    source_code = callback.data.split("|")[1]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Да, уверен", callback_data=f"al_dec_confirm|{source_code}")],
        [InlineKeyboardButton(text="Нет, вернуться", callback_data="ignore")]
    ])
    await callback.message.edit_text(callback.message.html_text + "\n\n❓ <b>Вы уверены, что хотите отклонить?</b>", reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data.startswith("al_dec_confirm|"))
async def diplomacy_decline_confirm(callback: CallbackQuery):
    source_code = callback.data.split("|")[1]
    source_mayor = db["cities"][source_code].get("owner_id")
    await callback.message.delete()
    await callback.answer("Отклонено.")
    if source_mayor:
        try:
            await bot.send_message(source_mayor, f"❌ Предложение о союзе было отклонено.", parse_mode="HTML")
        except: pass

# --- ОБЫЧНЫЕ ФУНКЦИИ ---
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

@dp.callback_query(F.data == "menu_apply")
async def start_application(callback: CallbackQuery, state: FSMContext):
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

@dp.callback_query(F.data.startswith("join_"))
async def start_join_request(callback: CallbackQuery, state: FSMContext):
    city_code = callback.data.split("_")[1]
    city_name = db["cities"][city_code]["name"]
    await state.update_data(city_code=city_code)
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
    last_reminder_check = time.time()
    
    while True:
        await asyncio.sleep(60) 
        
        current_time = time.time()
        
        if current_time - last_reminder_check > REMINDER_INTERVAL:
            if db.get("pending_rewards"):
                try:
                    await bot.send_message(ADMIN_ID, f"🔔 <b>НАПОМИНАНИЕ!</b>\n\nВы не выплатили награды {len(db['pending_rewards'])} игрокам за идеи!", parse_mode="HTML")
                except: pass
            
            users = db.get("all_users", [])
            for user_id in users:
                try:
                    await bot.send_message(user_id, AD_TEXT)
                    await asyncio.sleep(0.05)
                except: pass
            
            last_reminder_check = current_time

async def main():
    load_db()
    print("Бот запущен...")
    asyncio.create_task(broadcaster())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())