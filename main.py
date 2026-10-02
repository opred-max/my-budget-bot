import telebot
from telebot import types
import os
from datetime import datetime
import math
from flask import Flask
import threading
import logging
from telebot.apihelper import ApiException

# Настройка логирования для отслеживания ошибок на хостинге
logging.basicConfig(level=logging.INFO)

# =====================================================================
# КРИТИЧЕСКАЯ ЗАЩИТА ТОКЕНА ПРИ СТАРТЕ
# =====================================================================
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
if not TOKEN:
    raise ValueError("Критическая ошибка: Трейд-токен TELEGRAM_BOT_TOKEN не найден в переменных окружения!")

bot = telebot.TeleBot(TOKEN)
STATS_FILE = "monthly_stats.txt"

# Потокобезопасные замки для предотвращения конфликтов
file_lock = threading.Lock()
callback_lock = threading.Lock()

# Хранилище хэшей транзакций (Идемпотентность)
processed_callbacks = set()

# =====================================================================
# СИСТЕМА ХРАНЕНИЯ ДАННЫХ (БЕЗОПАСНАЯ СБОРКА СТРОКИ)
# =====================================================================
def save_to_stats(*, income_type, total, pocket, drive, school, cushion=0.0, holidays=0.0, health=0.0, auto=0.0, monuments=0.0, credit=0.0, clothes=0.0):
    """
    Записывает распределенный доход в файл статистики (Строго 14 колонок).
    Аргумент '*' гарантирует передачу только по именам для защиты от сдвигов.
    """
    try:
        month_key = datetime.now().strftime("%Y-%m")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        row = (
            f"{month_key}|{timestamp}|{income_type}|{total:.2f}|{pocket:.2f}|{drive:.2f}|"
            f"{school:.2f}|{cushion:.2f}|{holidays:.2f}|{health:.2f}|{auto:.2f}|{monuments:.2f}|{credit:.2f}|{clothes:.2f}\n"
        )
        with file_lock:
            with open(STATS_FILE, "a", encoding="utf-8") as f:
                f.write(row)
    except Exception as e:
        logging.error(f"Ошибка записи статистики: {e}")
# =====================================================================
# МАТЕМАТИЧЕСКОЕ ЯДРО: ОСНОВНОЙ ДОХОД (ОКРУГЛЕНИЕ ВСЕХ КОНВЕРТОВ ДО 100₽)
# =====================================================================
def calculate_cash_distribution(income):
    pocket = drive = holidays = health = auto = monuments = masya_school = 0.0
    
    # 1. Динамический процент жены строго через точки (30к -> 70%) и (69к -> 60%)
    p_wife = 0.70 - (0.10 * (income - 30000.0) / 39000.0)
    p_wife = max(0.48, min(0.73, p_wife))
    
    # Расчет доли жены с округлением вверх до 100 рублей
    wife_cash = math.ceil((income * p_wife) / 100) * 100
    c7 = income - wife_cash

    # 2. Динамические проценты конвертов твоей доли
    factor = 1.0 / (1.0 + (income / 50000.0))
    p_health = 0.05 + (0.03 * factor)
    p_school = 0.12
    p_auto = 0.11 - (0.04 * factor)
    p_drive = 0.15 - (0.15 * factor)
    p_holidays = 0.11 - (0.11 * factor)
    p_monuments = 0.05 - (0.05 * factor)
    
    # Базовый чистый Карман забирает остаток процентов до 100%
    p_pocket = 1.0 - (p_drive + p_school + p_holidays + p_health + p_auto + p_monuments)

    # Первичное распределение долей от чистой части c7
    pocket = c7 * p_pocket
    drive = c7 * p_drive
    masya_school = c7 * p_school
    holidays = c7 * p_holidays
    health = c7 * p_health
    auto = c7 * p_auto
    monuments = c7 * p_monuments
    
    # 3. ИСПРАВЛЕНО (Пункт 3): Налог 4% считается ТОЛЬКО от целевых конвертов, Карман исключен!
    clothes = (drive + holidays + health + auto + monuments) * 0.04
    drive, holidays, health, auto, monuments = drive*0.96, holidays*0.96, health*0.96, auto*0.96, monuments*0.96

    # 4. Применение жестких лимитов ПОСЛЕ налога (излишки уходят в Карман)
    if income > 75000 and monuments > 2000.0:
        pocket += (monuments - 2000.0)
        monuments = 2000.0
    if income > 125000:
        if holidays > 5500.0: pocket += (holidays - 5500.0); holidays = 5500.0
        if auto > 5000.0: pocket += (auto - 5000.0); auto = 5000.0
        if monuments > 2000.0: pocket += (monuments - 2000.0); monuments = 2000.0

    # 5. Округление абсолютно всех целевых фондов строго вниз до 100 рублей
    r_drive = math.floor(drive / 100) * 100
    r_holidays = math.floor(holidays / 100) * 100
    r_health = math.floor(health / 100) * 100
    r_auto = math.floor(auto / 100) * 100
    r_monuments = math.floor(monuments / 100) * 100
    r_masya_school = math.floor(masya_school / 100) * 100
    r_clothes = math.floor(clothes / 100) * 100
    
    # 6. ИСПРАВЛЕНО (Дефект 4): Карман теперь тоже СТРОГО кратен 100 рублям!
    allocated_targets = r_drive + r_holidays + r_health + r_auto + r_monuments + r_masya_school + r_clothes
    raw_pocket = (c7 - r_clothes) - (allocated_targets - r_clothes)
    r_pocket = math.floor(raw_pocket / 100) * 100
    
    # Технический хвост (копейки и рубли округления) уходит в колонку кубышки (cushion),
    # чтобы математический баланс сходился с c7 до копейки, но все конверты на экране были круглыми.
    r_cushion = c7 - (allocated_targets + r_pocket)

    mode_name = f"Точный график (Жена: {p_wife*100:.1f}% | Ты: {(1-p_wife)*100:.1f}%)"
    return mode_name, r_pocket, r_drive, r_masya_school, r_holidays, r_health, r_auto, r_monuments, r_clothes, wife_cash, c7, r_cushion
# =====================================================================
# МАТЕМАТИЧЕСКОЕ ЯДРО: ПОДРАБОТКИ (ПОРЯДОК СИНХРОНИЗИРОВАН)
# =====================================================================
def calculate_side_distribution(e2):
    pocket = drive = school = holidays = auto = 0.0
    
    if e2 > 15000:
        level_name = "🔥 5. ТУРБО Сверхдоход (Выше 15к)"
        pocket = 6000.0
        leftover = e2 - 6000.0
        drive, school, holidays, auto = leftover * 0.10, leftover * 0.10, leftover * 0.05, leftover * 0.10
        pocket += leftover * 0.65  
    else:
        if e2 <= 2000: 
            level_name = "🌱 1. Микро (до 2к)"
            p_pocket, p_drive, p_school, p_holidays, p_auto = 0.66, 0.10, 0.10, 0.00, 0.08
        elif e2 <= 5000: 
            level_name = "📈 2. Стандарт (2к - 5к)"
            p_pocket, p_drive, p_school, p_holidays, p_auto = 0.62, 0.15, 0.10, 0.05, 0.08
        elif e2 <= 10000: 
            level_name = "🚀 3. Профи (5к - 10к)"
            p_pocket, p_drive, p_school, p_holidays, p_auto = 0.60, 0.15, 0.10, 0.07, 0.08
        else: 
            level_name = "⚡ 4. Мега Профи (10к - 15к)"
            p_pocket, p_drive, p_school, p_holidays, p_auto = 0.59, 0.15, 0.12, 0.06, 0.08

        pocket, drive, school, holidays, auto = e2*p_pocket, e2*p_drive, e2*p_school, e2*p_holidays, e2*p_auto

    # Налог 4% на Гардероб
    clothes = (pocket + drive + holidays + auto) * 0.04
    pocket, drive, holidays, auto = pocket * 0.96, drive * 0.96, holidays * 0.96, auto * 0.96

    r_drive = math.floor(drive / 10) * 10
    r_school = math.floor(school / 10) * 10
    r_holidays = math.floor(holidays / 10) * 10
    r_auto = math.floor(auto / 10) * 10
    r_clothes = math.floor(clothes / 10) * 10

    # Все фонды подработок отсекаются одинаково
    if 0 < r_drive < 100: r_drive = 0.0
    if 0 < r_holidays < 100: r_holidays = 0.0
    if 0 < r_clothes < 100: r_clothes = 0.0
    if 0 < r_auto < 100: r_auto = 0.0
    if 0 < r_school < 100: r_school = 0.0

    allocated_except_pocket = r_drive + r_school + r_holidays + r_auto + r_clothes
    r_pocket = max(0.0, e2 - allocated_except_pocket)

    # ИСПРАВЛЕНО (Пункты 1 и 2): Жесткий порядок возврата переменных! r_auto на 6 месте, r_clothes на 7.
    return level_name, r_pocket, r_drive, r_school, r_holidays, r_auto, r_clothes

# =====================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ И ИНТЕРФЕЙС
# =====================================================================
def validate_amount(text):
    try:
        val = float(text.strip().replace(',', '.'))
        if val <= 0 or val > 9999999: return None  # Ограничение длины ввода против флуда байтами
        return val
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

def is_menu_command(text, chat_id):
    if text in ["💵 Основной доход", "🚀 Подработка", "📊 Ежемесячный отчет", "/start", "/help"]:
        # ИСПРАВЛЕНО (Дефект 1 UI): Полностью сбрасываем застрявшие шаги ввода при клике на меню
        bot.clear_step_handler_by_chat_id(chat_id)
        return True
    return False
# =====================================================================
# ХЭНДЛЕРЫ КНОПОК МЕНЮ И ШАГОВ ВВОДА
# =====================================================================
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "👋 **Financial Engine v9.0 [CEIL EDITION] активирован.**\n"
        "Основной доход: доля жены теперь округляется строго вверх до 100 ₽.\n"
        "Твои целевые конверты бьются по 100 ₽, подработки — по 10 ₽.\n\n"
        "Используй кнопки меню для расчетов 👇"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard(), parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "💵 Основной доход")
def ask_cash(message):
    msg = bot.send_message(message.chat.id, "💵 Введите сумму основного дохода:")
    bot.register_next_step_handler(msg, process_cash)

def process_cash(message):
    if is_menu_command(message.text, message.chat.id): return
    income = validate_amount(message.text)
    if income is None:
        msg = bot.send_message(message.chat.id, "❌ **Неверный формат числа!** Пожалуйста, введите положительное число:")
        bot.register_next_step_handler(msg, process_cash)
        return

    try:
        mode_name, r_pocket, r_drive, r_school, r_holidays, r_health, r_auto, r_monuments, r_clothes, wife_cash, c7, r_cushion = calculate_cash_distribution(income)

        report = (
            f"📊 **РАСЧЕТ ОСНОВНОГО ДОХОДА ({income:,.0f} ₽)**\n"
            f"⚙️ Режим: `{mode_name}`\n\n"
            f"💵 **Наличные (От продаж):**\n"
            f"└ 👩 Жене наличными (Вверх до 100 ₽): **{wife_cash:,.0f} ₽**\n"
            f"└ 🧔 Твоя чистая доля: **{c7:,.0f} ₽**\n\n"
            f"🗂 **Распределение по конвертам (Шаг 100 ₽):**\n"
            f"🛍 Конверт «Карман»: **{r_pocket:,.0f} ₽**\n"
        )
        if r_drive > 0: report += f"🏎 Конверт «Драйв»: **{r_drive:,.0f} ₽**\n"
        if r_clothes > 0: report += f"👔 Конверт «Гардероб» (Шмотки): **{r_clothes:,.0f} ₽**\n"
        if r_holidays > 0: report += f"🎉 Фонд праздников: **{r_holidays:,.0f} ₽**\n"
        if r_health > 0: report += f"🩺 Конверт «Здоровье»: **{r_health:,.0f} ₽**\n"
        if r_auto > 0: report += f"🚗 Автофонд: **{r_auto:,.0f} ₽**\n"
        if r_school > 0: report += f"🎒 Мася школа: **{r_school:,.0f} ₽**\n"
        if r_monuments > 0: report += f"🪦 Конверт «Памятники»: **{r_monuments:,.0f} ₽**\n"
        if r_cushion > 0: report += f"🪙 Кубышка (Остаток округлений): **{r_cushion:,.2f} ₽**\n"
        
        tx_hash = f"sm_{int(income)}_{datetime.now().strftime('%M%S')}"
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
    if is_menu_command(message.text, message.chat.id): return
    e2 = validate_amount(message.text)
    if e2 is None:
        msg = bot.send_message(message.chat.id, "❌ **Неверный формат числа!** Пожалуйста, введите корректную сумму подработки:")
        bot.register_next_step_handler(msg, process_side)
        return

    try:
        level_name, r_pocket, r_drive, r_school, r_holidays, r_auto, r_clothes = calculate_side_distribution(e2)

        report = (
            f"🚀 **РАСЧЕТ ПОДРАБОТКИ ({e2:,.0f} ₽)**\n"
            f"⚡ Уровень дохода: `{level_name}`\n\n"
            f"🗂 **В твои конверты (Шаг 10 ₽):**\n"
            f"🛍 Конверт «Карман»: **{r_pocket:,.0f} ₽**\n"
        )
        if r_drive > 0: report += f"🏎 Конверт «Драйв»: **{r_drive:,.0f} ₽**\n"
        if r_clothes > 0: report += f"👔 Конверт «Гардероб» (Шмотки): **{r_clothes:,.0f} ₽**\n"
        if r_school > 0: report += f"🎒 Конверт «Мася школа»: **{r_school:,.0f} ₽**\n"
        if r_holidays > 0: report += f"🎉 Фонд праздников: **{r_holidays:,.0f} ₽**\n"
        if r_auto > 0: report += f"🚗 Автофонд: **{r_auto:,.0f} ₽**\n"
        
        tx_hash = f"ss_{int(e2)}_{datetime.now().strftime('%M%S')}"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📝 Подтвердить и записать доход", callback_data=tx_hash))
        bot.send_message(message.chat.id, report, reply_markup=markup, parse_mode='Markdown')
    except Exception as e:
        logging.error(f"Ошибка подработки: {e}")
        bot.send_message(message.chat.id, "❌ Ошибка подработки.")

# =====================================================================
# ЛАКОНИЧНЫЙ ЕЖЕМЕСЯЧНЫЙ ОТЧЕТ
# =====================================================================
@bot.message_handler(func=lambda m: m.text == "📊 Ежемесячный отчет")
def show_monthly_report(message):
    now = datetime.now()
    current_month = now.strftime("%Y-%m")
    prev_month = f"{now.year - 1}-12" if now.month == 1 else f"{now.year}-{now.month - 1:02d}"
    total_main = total_side = total_prev = 0.0
    
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("|")
                if len(parts) < 14: continue 
                
                net_personal_sum = (
                    float(parts[4]) + float(parts[5]) + float(parts[6]) + 
                    float(parts[7]) + float(parts[8]) + float(parts[9]) + 
                    float(parts[10]) + float(parts[11]) + float(parts[13])
                )
                if parts[0] == prev_month: total_prev += net_personal_sum
                if parts[0] == current_month:
                    if parts[2] == "основной": total_main += net_personal_sum
                    else: total_side += net_personal_sum
                        
    total_earned = total_main + total_side
    msg = (
        f"📊 **ФИНАНСОВЫЙ ОТЧЕТ**\n📅 Период: `{current_month}`\n═══════════════════════════\n\n"
        f"📈 **ДВИЖЕНИЕ ЧИСТОГО КАПИТАЛА:**\n"
        f"├ 💰 Личных средств зашло: **{total_earned:,.2f} ₽**\n"
        f"├ 💵 Основной доход: {total_main:,.2f} ₽\n"
        f"└ 🚀 Из подработок: {total_side:,.2f} ₽\n\n"
        f"═══════════════════════════\n"
        f"📅 **СРАВНЕНИЕ:**\n"
        f"└ ⏪ Твоя чистая доля в `{prev_month}`: **{total_prev:,.2f} ₽**"
    )
    bot.send_message(message.chat.id, msg, parse_mode='Markdown')
# =====================================================================
# ИДЕМПОТЕНТНЫЙ CALLBACK ОБРАБОТЧИК (ПОРЯДОК СИНХРОНИЗИРОВАН)
# =====================================================================
@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    global processed_callbacks
    try:
        with callback_lock:
            if call.data in processed_callbacks:
                bot.answer_callback_query(call.id, "Эта транзакция уже записана!")
                return
            processed_callbacks.add(call.data)
            if len(processed_callbacks) > 200: processed_callbacks.clear()

        parts = call.data.split("_")
        action = parts[0]   
        amount = float(parts[1])  

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
            level_name, r_pocket, r_drive, r_school, r_holidays, r_auto, r_clothes = calculate_side_distribution(amount)
            save_to_stats(income_type="подработка", total=amount, pocket=r_pocket, drive=r_drive, school=r_school, holidays=r_holidays, auto=r_auto, clothes=r_clothes)
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
