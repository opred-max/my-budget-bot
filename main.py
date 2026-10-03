import telebot
from telebot import types
import os
from datetime import datetime
import math
from flask import Flask
import threading
import logging
from telebot.apihelper import ApiException
from collections import deque
import sqlite3

# Настройка логирования для отслеживания ошибок на хостинге
logging.basicConfig(level=logging.INFO)

# =====================================================================
# КРИТИЧЕСКАЯ ЗАЩИТА ТОКЕНА ПРИ СТАРТЕ
# =====================================================================
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
if not TOKEN:
    raise ValueError("Критическая ошибка: Трейд-токен TELEGRAM_BOT_TOKEN не найден в переменных окружения!")

bot = telebot.TeleBot(TOKEN)
DB_FILE = "finance.db"

# Потокобезопасные замки для предотвращения конфликтов
db_lock = threading.Lock()
callback_lock = threading.Lock()

# Потокобезопасная queue для защиты от дублирования транзакций
processed_callbacks = deque(maxlen=200)
# =====================================================================
# ИНИЦИАЛИЗАЦИЯ И СИСТЕМА ХРАНЕНИЯ ДАННЫХ SQLITE3
# =====================================================================
def init_db():
    """Создает таблицу stats в SQLite с 14 классическими колонками структуры лога"""
    with db_lock:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        conn.execute("PRAGMA journal_mode=WAL;")  # Оптимизация под многопоточность Flask/Бот
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month_key TEXT,
                timestamp TEXT,
                income_type TEXT,
                total REAL,
                pocket REAL,
                drive REAL,
                school REAL,
                cushion REAL,
                holidays REAL,
                health REAL,
                auto REAL,
                monuments REAL,
                credit REAL,
                clothes REAL
            )
        ''')
        conn.commit()
        conn.close()

init_db()

def save_to_stats(*, income_type, total, pocket, drive, school, cushion=0.0, holidays=0.0, health=0.0, auto=0.0, monuments=0.0, credit=0.0, clothes=0.0):
    """Потокобезопасно записывает распределенный доход в базу данных SQLite"""
    try:
        month_key = datetime.now().strftime("%Y-%m")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with db_lock:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO stats (
                    month_key, timestamp, income_type, total, pocket, drive, 
                    school, cushion, holidays, health, auto, monuments, credit, clothes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                month_key, timestamp, income_type, total, pocket, drive,
                school, cushion, holidays, health, auto, monuments, credit, clothes
            ))
            conn.commit()
            conn.close()
    except Exception as e:
        logging.error(f"Ошибка записи в SQLite: {e}")

# =====================================================================
# МАТЕМАТИЧЕСКОЕ ЯДРО: ОСНОВНОЙ ДОХОД
# =====================================================================
def calculate_cash_distribution(income):
    pocket = drive = holidays = health = auto = monuments = masya_school = 0.0
    
    # 1. График долей супругов: при доходе от 100к жестко 60%, иначе плавный расчет на интервале 30к-100к
    if income >= 100000.0:
        p_wife = 0.60
    else:
        p_wife = 0.70 - (0.10 * (income - 30000.0) / 70000.0)
        p_wife = max(0.48, min(0.73, p_wife))
    
    wife_cash = math.ceil((income * p_wife) / 100) * 100
    c7 = income - wife_cash

    # 2. Налог 4% на Одежду (Гардероб) напрямую от полной чистой доли c7
    clothes = c7 * 0.04
    c7_usable = c7 - clothes

    # 3. Динамические проценты конвертов внутри пригодной для распределения доли c7_usable
    factor = 1.0 / (1.0 + (income / 50000.0))
    p_health = 0.05 + (0.03 * factor)
    p_school = 0.12
    p_auto = 0.11 - (0.04 * factor)
    p_drive = 0.15 - (0.15 * factor)
    p_holidays = 0.11 - (0.11 * factor)
    p_monuments = 0.05 - (0.05 * factor)
    
    # Режим Выживания: новые калиброванные лимиты отключения накопительных фондов
    if income <= 54000.0:
        p_drive = 0.0      
        p_holidays = 0.0   

    p_pocket = 1.0 - (p_drive + p_school + p_holidays + p_health + p_auto + p_monuments)

    # Распределение сумм
    pocket = c7_usable * p_pocket
    drive = c7_usable * p_drive
    masya_school = c7_usable * p_school
    holidays = c7_usable * p_holidays
    health = c7_usable * p_health
    auto = c7_usable * p_auto
    monuments = c7_usable * p_monuments

    # Включение Памятников строго при условии, что доля c7 > 25 000 руб
    if c7 <= 25000.0:
        pocket += monuments  
        monuments = 0.0

    # 4. Применение жестких upper-лимитов (Снижение планки со 125к до 100к)
    if income > 75000 and monuments > 2000.0:
        pocket += (monuments - 2000.0); monuments = 2000.0
    if income > 100000.0:
        if holidays > 5500.0: 
            pocket += (holidays - 5500.0)
            holidays = 5500.0
        if auto > 5000.0: 
            pocket += (auto - 5000.0)
            auto = 5000.0
        if monuments > 2000.0: 
            pocket += (monuments - 2000.0)
            monuments = 2000.0

    # 5. Округление целевых фондов строго вниз до 100 рублей
    r_drive = math.floor(drive / 100) * 100
    r_holidays = math.floor(holidays / 100) * 100
    r_health = math.floor(health / 100) * 100
    r_auto = math.floor(auto / 100) * 100
    r_monuments = math.floor(monuments / 100) * 100
    r_masya_school = math.floor(masya_school / 100) * 100
    r_clothes = math.floor(clothes / 100) * 100
    
    # 6. Расчет округленного кармана на базе очищенной c7_usable без повторных вычетов одежды
    allocated_except_pocket_and_clothes = r_drive + r_holidays + r_health + r_auto + r_monuments + r_masya_school
    r_pocket = max(0.0, math.floor((c7_usable - allocated_except_pocket_and_clothes) / 100) * 100)
    r_cushion = c7 - (allocated_except_pocket_and_clothes + r_pocket + r_clothes)

    mode_name = f"Динамический режим (Жена: {p_wife*100:.1f}% | Ты: {(1-p_wife)*100:.1f}%)"
    return mode_name, r_pocket, r_drive, r_masya_school, r_holidays, r_health, r_auto, r_monuments, r_clothes, wife_cash, c7, r_cushion
# =====================================================================
# МАТЕМАТИЧЕСКОЕ ЯДРО: ПОДРАБОТКИ
# =====================================================================
def calculate_side_distribution(e2):
    pocket = drive = school = holidays = auto = 0.0
    
    # 1. Сквозной вычет налога 4% на одежду в самом начале и очистка базы
    clothes = e2 * 0.04
    e2_usable = e2 - clothes

    # 2. Калибровочные диапазоны долей подработок от e2_usable
    if e2_usable <= 2000.0:
        level_name = "🌱 1. Микро (до 2к)"
        pocket = e2_usable * 0.66
        drive = e2_usable * 0.10
        school = e2_usable * 0.10
        auto = e2_usable * 0.08
        holidays = 0.0
    elif e2_usable <= 7500.0:
        level_name = "📈 2. Стандарт (2к - 7.5к)"
        pocket = e2_usable * 0.65
        drive = e2_usable * 0.15
        school = e2_usable * 0.10
        auto = e2_usable * 0.10
        holidays = 0.0
    elif e2_usable <= 12000.0:
        level_name = "🚀 3. Профи (7.5к - 12к)"
        pocket = e2_usable * 0.60
        drive = e2_usable * 0.15
        school = e2_usable * 0.10
        auto = e2_usable * 0.10
        holidays = e2_usable * 0.05
    else:
        level_name = "🔥 4. ТУРБО Сверхдоход (Выше 12к)"
        pocket = 7000.0
        leftover = e2_usable - 7000.0
        pocket += leftover * 0.60
        drive = leftover * 0.15
        school = leftover * 0.10
        auto = leftover * 0.10
        holidays = leftover * 0.05

    # 3. Реализация классического округления до 10 рублей и гибридного триггера
    # Математическое округление до десятков
    round_drive = round(drive, -1)
    round_school = round(school, -1)
    round_holidays = round(holidays, -1)
    round_auto = round(auto, -1)
    round_clothes = round(clothes, -1)

    # Применение триггера: > 50.0 -> 100.0 рублей, иначе -> 0.0 рублей
    r_drive = 100.0 if round_drive > 50.0 else 0.0
    r_school = 100.0 if round_school > 50.0 else 0.0
    r_holidays = 100.0 if round_holidays > 50.0 else 0.0
    r_auto = 100.0 if round_auto > 50.0 else 0.0
    r_clothes = 100.0 if round_clothes > 50.0 else 0.0

    # Карман забирает ВЕСЬ чистый остаток от исходной грязной суммы e2
    r_pocket = max(0.0, e2 - (r_drive + r_school + r_holidays + r_auto + r_clothes))
    
    # Фиксация технической Кубышки
    r_cushion = 0.0

    return level_name, r_pocket, r_drive, r_school, r_holidays, r_auto, r_clothes, r_cushion

# =====================================================================
# ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ И КЛАВИАТУРА
# =====================================================================
def validate_amount(text):
    try:
        val = float(text.strip().replace(',', '.'))
        if val <= 0 or val > 9999999: return None
        return math.floor(val)
    except ValueError:
        return None

def get_main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_cash = types.KeyboardButton("💵 Основной доход")
    btn_side = types.KeyboardButton("🚀 Подработка")
    btn_report = types.KeyboardButton("📊 Ежемесячный отчет")
    keyboard.add(btn_cash, btn_side)
    keyboard.add(btn_report)
    return keyboard

def is_menu_command(text, message):
    if text in ["💵 Основной доход", "🚀 Подработка", "📊 Ежемесячный отчет", "/start", "/help"]:
        bot.clear_step_handler_by_chat_id(message.chat.id)
        threading.Thread(target=bot.process_new_messages, args=([message],), daemon=True).start()
        return True
    return False
# =====================================================================
# ХЭНДЛЕРЫ КНОПОК МЕНЮ И ШАГОВ ВВОДА
# =====================================================================
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "👋 **Financial Engine v10.6 [MONOLITH CALIBRATED] активирован.**\n"
        "Ликвидированы дедлоки, исправлен учет налогов, обеспечена типобезопасность.\n"
        "Ядро подработок переписано: классический round() и гибридный триггер 50 ₽ внедрены.\n\n"
        "Используй кнопки меню для расчетов 👇"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard(), parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "💵 Основной доход")
def ask_cash(message):
    msg = bot.send_message(message.chat.id, "💵 Введите сумму основного дохода:")
    bot.register_next_step_handler(msg, process_cash)

def process_cash(message):
    if is_menu_command(message.text, message): return
    income = validate_amount(message.text)
    if income is None:
        msg = bot.send_message(message.chat.id, "❌ **Неверный формат числа!** Введите положительное целое число:")
        bot.register_next_step_handler(msg, process_cash)
        return

    try:
        mode_name, r_pocket, r_drive, r_school, r_holidays, r_health, r_auto, r_monuments, r_clothes, wife_cash, c7, r_cushion = calculate_cash_distribution(income)

        report = (
            f"📊 **РАСЧЕТ ОСНОВНОГО ДОХОДА ({income:,.0f} ₽)**\n"
            f"⚙️ `{mode_name}`\n\n"
            f"💵 **Наличные (От продаж):**\n"
            f"└ 👩 Жене наличными: **{wife_cash:,.0f} ₽**\n"
            f"└ 🧔 Твоя чистая доля: **{c7:,.0f} ₽**\n\n"
            f"🗂 **Распределение по конвертам:**\n"
            f"🛍 Конверт «Карман»: **{r_pocket:,.0f} ₽**\n"
        )
        if r_drive > 0: report += f"🏎 Конверт «Драйв»: **{r_drive:,.0f} ₽**\n"
        if r_clothes > 0: report += f"👔 Конверт «Гардероб» (Шмотки): **{r_clothes:,.0f} ₽**\n"
        if r_holidays > 0: report += f"🎉 Фонд праздников: **{r_holidays:,.0f} ₽**\n"
        if r_health > 0: report += f"🩺 Конверт «Здоровье»: **{r_health:,.0f} ₽**\n"
        if r_auto > 0: report += f"🚗 Автофонд: **{r_auto:,.0f} ₽**\n"
        if r_school > 0: report += f"🎒 Мася школа: **{r_school:,.0f} ₽**\n"
        if r_monuments > 0: report += f"🪦 Конверт «Памятники»: **{r_monuments:,.0f} ₽**\n"
        
        tx_hash = f"sm_{income}_{datetime.now().strftime('%M%S')}"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📝 Подтвердить и записать доход", callback_data=tx_hash))
        bot.send_message(message.chat.id, report, reply_markup=markup, parse_mode='Markdown')
    except Exception as e:
        logging.error(f"Ошибка основного дохода: {e}")
        bot.send_message(message.chat.id, "❌ Произошла ошибка расчетов.")

@bot.message_handler(func=lambda m: m.text == "🚀 Подработка")
def ask_side(message):
    msg = bot.send_message(message.chat.id, "🚀 Введите сумму случайной подработки:")
    bot.register_next_step_handler(msg, process_side)

def process_side(message):
    if is_menu_command(message.text, message): return
    e2 = validate_amount(message.text)
    if e2 is None:
        msg = bot.send_message(message.chat.id, "❌ **Неверный формат числа!** Введите сумму подработки:")
        bot.register_next_step_handler(msg, process_side)
        return

    try:
        level_name, r_pocket, r_drive, r_school, r_holidays, r_auto, r_clothes, r_cushion = calculate_side_distribution(e2)

        report = (
            f"🚀 **РАСЧЕТ ПОДРАБОТКИ ({e2:,.0f} ₽)**\n"
            f"⚡ Уровень дохода: `{level_name}`\n\n"
            f"🗂 **В твои конверты:**\n"
            f"🛍 Конверт «Карман»: **{r_pocket:,.0f} ₽**\n"
        )
        if r_drive > 0: report += f"🏎 Конверт «Драйв»: **{r_drive:,.0f} ₽**\n"
        if r_clothes > 0: report += f"👔 Конверт «Гардероб» (Шмотки): **{r_clothes:,.0f} ₽**\n"
        if r_school > 0: report += f"🎒 Конверт «Мася школа»: **{r_school:,.0f} ₽**\n"
        if r_holidays > 0: report += f"🎉 Фонд праздников: **{r_holidays:,.0f} ₽**\n"
        if r_auto > 0: report += f"🚗 Автофонд: **{r_auto:,.0f} ₽**\n"
        
        tx_hash = f"ss_{e2}_{datetime.now().strftime('%M%S')}"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📝 Подтвердить и записать доход", callback_data=tx_hash))
        bot.send_message(message.chat.id, report, reply_markup=markup, parse_mode='Markdown')
    except Exception as e:
        logging.error(f"Ошибка подработки: {e}")
        bot.send_message(message.chat.id, "❌ Ошибка подработки.")
# =====================================================================
# ЕЖЕМЕСЯЧНЫЙ ОТЧЕТ (ПОЛНАЯ СИНХРОНИЗАЦИЯ СТРУКТУРЫ SELECT ЗАПРОСОВ)
# =====================================================================
@bot.message_handler(func=lambda m: m.text == "📊 Ежемесячный отчет")
def show_monthly_report(message):
    now = datetime.now()
    current_month = now.strftime("%Y-%m")
    prev_month = f"{now.year - 1}-12" if now.month == 1 else f"{now.year}-{now.month - 1:02d}"
    total_main = total_side = total_prev = 0.0
    
    try:
        with db_lock:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            # Выборка: income_type(0), pocket(1), drive(2), school(3), cushion(4), holidays(5), health(6), auto(7), monuments(8), clothes(9)
            cursor.execute('SELECT income_type, pocket, drive, school, cushion, holidays, health, auto, monuments, clothes FROM stats WHERE month_key = ?', (current_month,))
            rows = cursor.fetchall()
            
            # Накапливаем данные текущего месяца с условным прибавлением cushion (r) для основного дохода
            for r in rows:
                net_sum = (
                    float(r or 0) + float(r or 0) + float(r or 0) + 
                    float(r or 0) + float(r or 0) + float(r or 0) + 
                    float(r or 0) + float(r or 0)
                )
                if r == "основной":
                    net_sum += float(r or 0)
                    total_main += net_sum
                else:
                    total_side += net_sum
            
            cursor.execute('SELECT income_type, pocket, drive, school, cushion, holidays, health, auto, monuments, clothes FROM stats WHERE month_key = ?', (prev_month,))
            prev_rows = cursor.fetchall()
            
            # Накапливаем данные прошлого месяца с условным прибавлением cushion (pr) для основного дохода
            for pr in prev_rows:
                net_prev_sum = (
                    float(pr or 0) + float(pr or 0) + float(pr or 0) + 
                    float(pr or 0) + float(pr or 0) + float(pr or 0) + 
                    float(pr or 0) + float(pr or 0)
                )
                if pr == "основной":
                    net_prev_sum += float(pr or 0)
                total_prev += net_prev_sum
                
            conn.close()
    except Exception as e:
        logging.error(f"Ошибка чтения отчета из SQLite: {e}")

    total_earned = total_main + total_side
    msg = (
        f"📊 **ФИНАНСОВЫЙ ОТЧЕТ**\n📅 Период: `{current_month}`\n═══════════════════════════\n\n"
        f"📈 **ДВИЖЕНИЕ ЧИСТОГО КАПИТАЛА:**\n"
        f"├ 💰 Личных средств зашло: **{total_earned:,.2f} ₽**\n"
        f"├ 💵 Основной доход: {total_main:,.2f} ₽\n"
        f"└ 🚀 Из подработок: {total_side:,.2f} ₽\n\n"
        f"═══════════════════════════\n"
        f"📅 **СРАВНЕНИЕ:**\n"
        f"└ ⏪ Твоя чистая доля in `{prev_month}`: **{total_prev:,.2f} ₽**"
    )
    bot.send_message(message.chat.id, msg, parse_mode='Markdown')

# =====================================================================
# CALLBACK ОБРАБОТЧИК
# =====================================================================
@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    global processed_callbacks
    try:
        with callback_lock:
            if call.data in processed_callbacks:
                bot.answer_callback_query(call.id, "Эта транзакция уже записана!")
                return
            processed_callbacks.append(call.data)

        parts = call.data.split("_")
        action = parts   
        amount = int(parts)  

        if action == "sm":
            mode_name, r_pocket, r_drive, r_school, r_holidays, r_health, r_auto, r_monuments, r_clothes, wife_cash, c7, r_cushion = calculate_cash_distribution(amount)
            save_to_stats(income_type="основной", total=amount, pocket=r_pocket, drive=r_drive, school=r_school, holidays=r_holidays, health=r_health, auto=r_auto, monuments=r_monuments, clothes=r_clothes, cushion=r_cushion)
            bot.answer_callback_query(call.id, "Доход успешно зафиксирован!")
            
            new_text = (
                f"📊 **РАСЧЕТ ОСНОВНОГО ДОХОДА ({amount:,.0f} ₽)**\n"
                f"⚙️ `{mode_name}`\n\n"
                f"✅ **ДОХОД УСПЕШНО ПОДТВЕРЖДЕН И ЗАПИСАН В БАЗУ**"
            )
            try: bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=new_text, parse_mode='Markdown')
            except ApiException: pass 
            
        elif action == "ss":
            level_name, r_pocket, r_drive, r_school, r_holidays, r_auto, r_clothes, r_cushion = calculate_side_distribution(amount)
            save_to_stats(income_type="подработка", total=amount, pocket=r_pocket, drive=r_drive, school=r_school, holidays=r_holidays, auto=r_auto, clothes=r_clothes, cushion=r_cushion, health=0.0, monuments=0.0)
            bot.answer_callback_query(call.id, "Запись обновлена!")
            
            new_text = (
                f"🚀 **РАСЧЕТ ПОДРАБОТКИ ({amount:,.0f} ₽)**\n"
                f"⚡ `{level_name}`\n\n"
                f"✅ **ПОДРАБОТКА УСПЕШНО ПОДТВЕРЖДЕНА И ЗАПИСАНА В БАЗУ**"
            )
            try: bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=new_text, parse_mode='Markdown')
            except ApiException: pass
    except Exception as e:
        logging.error(f"Ошибка в callback: {e}")
        bot.answer_callback_query(call.id, "❌ Ошибка подтверждения")

# =====================================================================
# ЗАПУСК FLASK И БОТА
# =====================================================================
app = Flask('')
@app.route('/')
def home(): return "Финансовый движок активен!"

def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    bot.infinity_polling(skip_pending=True)
