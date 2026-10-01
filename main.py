import telebot
from telebot import types
import os
from datetime import datetime
import math
from flask import Flask
import threading
import logging

# Настройка логирования для отслеживания ошибок на хостинге
logging.basicConfig(level=logging.INFO)

# =====================================================================
# ТОКЕН БОТА И НАСТРОЙКИ ФАЙЛОВ
# =====================================================================
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
bot = telebot.TeleBot(TOKEN)

# Файл статистики сохраняется для ведения месячных отчетов
STATS_FILE = "monthly_stats.txt"

# Потокобезопасный замок для предотвращения конфликтов записи в файл
file_lock = threading.Lock()

# =====================================================================
# СИСТЕМА ХРАНЕНИЯ ДАННЫХ
# =====================================================================
def save_to_stats(income_type, total, pocket, drive, school, cushion, holidays=0, health=0, auto=0, monuments=0, credit=0, clothes=0):
    """Записывает распределенный доход в файл статистики"""
    try:
        month_key = datetime.now().strftime("%Y-%m")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        row = (
            f"{month_key}|{timestamp}|{income_type}|{total:.2f}|{pocket:.2f}|{drive:.2f}|"
            f"{school:.2f}|{cushion:.2f}|{holidays:.2f}|{health:.2f}|{auto:.2f}|{monuments:.2f}|0.00|{clothes:.2f}\n"
        )
        with file_lock:
            with open(STATS_FILE, "a", encoding="utf-8") as f:
                f.write(row)
    except Exception as e:
        logging.error(f"Ошибка записи статистики: {e}")
# =====================================================================
# МАТЕМАТИЧЕСКОЕ ЯДРО: ОСНОВНОЙ ДОХОД
# =====================================================================
def calculate_cash_distribution(income):
    pocket = drive = holidays = health = auto = monuments = masya_school = 0.0
    
    # Распределение долей между мужем и женой. Проценты бывшей подушки перелиты в Карман.
    if income <= 37500:
        mode_name = "🟥 Уровень 1: Выживание (до 37.5к)"
        c7 = income * 0.35         
        p_pocket, p_drive, p_school, p_holidays, p_health, p_auto, p_monuments = 0.73, 0.00, 0.12, 0.00, 0.08, 0.07, 0.00
    elif income <= 75000:
        mode_name = "🟧 Уровень 2: Стабилизация (от 37.5к до 75к)"
        c7 = income * 0.35         
        p_pocket, p_drive, p_school, p_holidays, p_health, p_auto, p_monuments = 0.50, 0.15, 0.12, 0.15, 0.08, 0.12, 0.00
    elif income <= 125000:
        mode_name = "🟨 Уровень 3: Развитие (от 75к до 125к)"
        c7 = income * 0.40         
        p_pocket, p_drive, p_school, p_holidays, p_health, p_auto, p_monuments = 0.57, 0.14, 0.12, 0.10, 0.06, 0.10, 0.05
    else:
        mode_name = "♾ Уровень 4: Жирный режим (выше 125к)"
        c7 = income * 0.40         
        p_pocket, p_drive, p_school, p_holidays, p_health, p_auto, p_monuments = 0.48, 0.15, 0.12, 0.10, 0.05, 0.10, 0.05

    pocket, drive, masya_school, holidays, health, auto, monuments = (
        c7*p_pocket, c7*p_drive, c7*p_school, c7*p_holidays, c7*p_health, c7*p_auto, c7*p_monuments
    )
    
    # Жесткие лимиты до налога с переливом остатка в Карман
    if income > 75000 and monuments > 2000.0:
        pocket += (monuments - 2000.0)
        monuments = 2000.0
        
    if income > 125000:
        if holidays > 5500.0: pocket += (holidays - 5500.0); holidays = 5500.0
        if auto > 5000.0: pocket += (auto - 5000.0); auto = 5000.0
        if monuments > 2000.0: pocket += (monuments - 2000.0); monuments = 2000.0

    # Сквозной налог 4% (Школа Маси освобождена)
    clothes = (pocket + drive + holidays + health + auto + monuments) * 0.04
    pocket, drive, holidays, health, auto, monuments = pocket*0.96, drive*0.96, holidays*0.96, health*0.96, auto*0.96, monuments*0.96

    # Округление целевых фондов строго вниз до 10 руб
    r_drive = math.floor(drive / 10) * 10
    r_holidays = math.floor(holidays / 10) * 10
    r_health = math.floor(health / 10) * 10
    r_auto = math.floor(auto / 10) * 10
    r_monuments = math.floor(monuments / 10) * 10
    r_masya_school = math.floor(masya_school / 10) * 10
    r_clothes = math.floor(clothes / 10) * 10
    
    # Балансирующий Карман собирает все остатки округлений
    allocated_except_pocket = r_drive + r_holidays + r_health + r_auto + r_monuments + r_masya_school + r_clothes
    r_pocket = c7 - allocated_except_pocket

    return mode_name, r_pocket, r_drive, r_masya_school, r_holidays, r_health, r_auto, r_monuments, r_clothes
# =====================================================================
# МАТЕМАТИЧЕСКОЕ ЯДРО: ПОДРАБОТКИ
# =====================================================================
def calculate_side_distribution(e2):
    pocket = drive = school = holidays = auto = 0.0
    
    if e2 > 15000:
        level_name = "🔥 5. ТУРБО Сверхдоход (Выше 15к)"
        pocket = 6000.0
        leftover = e2 - 6000.0
        drive, school, holidays, auto = leftover * 0.10, leftover * 0.10, leftover * 0.05, leftover * 0.10
        pocket += leftover * 0.65  # Проценты бывшей подушки ушли в карман подработок
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

    # Налог 4%
    clothes = (pocket + drive + holidays + auto) * 0.04
    pocket, drive, holidays, auto = pocket * 0.96, drive * 0.96, holidays * 0.96, auto * 0.96

    r_drive = math.floor(drive / 10) * 10
    r_school = math.floor(school / 10) * 10
    r_holidays = math.floor(holidays / 10) * 10
    r_clothes = math.floor(clothes / 10) * 10
    r_auto = math.floor(auto / 10) * 10

    if 0 < r_drive < 100: r_drive = 0.0
    if 0 < r_holidays < 100: r_holidays = 0.0
    if 0 < r_clothes < 100: r_clothes = 0.0
    if 0 < r_auto < 100: r_auto = 0.0
    if 0 < r_school < 100: r_school = 100.0

    allocated_except_pocket = r_drive + r_school + r_holidays + r_clothes + r_auto
    r_pocket = e2 - allocated_except_pocket

    return level_name, r_pocket, r_drive, r_school, r_holidays, r_clothes, r_auto

# =====================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ И ИНТЕРФЕЙС
# =====================================================================
def validate_amount(text):
    try:
        val = float(text.strip().replace(',', '.'))
        if val <= 0: return None
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

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "👋 **Financial Engine v7.0 [CLEAN EDITION] активирован.**\n"
        "Подушка безопасности и кредиты полностью удалены из системы.\n"
        "Остатки и налоги балансируются копейка в копейку.\n\n"
        "Используй кнопки меню для расчетов 👇"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard(), parse_mode='Markdown')
# =====================================================================
# ХЭНДЛЕРЫ КНОПОК МЕНЮ И ШАГОВ ВВОДА
# =====================================================================
@bot.message_handler(func=lambda m: m.text == "💵 Основной доход")
def ask_cash(message):
    msg = bot.send_message(message.chat.id, "💵 Введите сумму основного дохода:")
    bot.register_next_step_handler(msg, process_cash)

def process_cash(message):
    if message.text in ["💵 Основной доход", "🚀 Подработка", "📊 Ежемесячный отчет"]: return
    try:
        income = validate_amount(message.text)
        if income is None:
            bot.send_message(message.chat.id, "❌ **Ошибка ввода!** Введите корректное число.")
            return

        wife_cash = income * 0.65 if income <= 75000 else income * 0.60
        c7 = income * 0.35 if income <= 75000 else income * 0.40
        
        mode_name, r_pocket, r_drive, r_masya_school, r_holidays, r_health, r_auto, r_monuments, r_clothes = calculate_cash_distribution(income)

        report = (
            f"📊 **РАСЧЕТ ОСНОВНОГО ДОХОДА ({income:,.0f} ₽)**\n"
            f"⚙️ Режим твоей доли: `{mode_name}`\n\n"
            f"💵 **Наличные (От продаж):**\n"
            f"└ 👩 Жене наличными: **{wife_cash:,.0f} ₽**\n"
            f"└ 🧔 Твоя чистая доля: **{c7:,.0f} ₽**\n\n"
            f"🗂 **Распределение по конвертам:**\n"
        )
        if r_pocket > 0: report += f"🛍 Конверт «Карман»: **{r_pocket:,.0f} ₽**\n"
        if r_drive > 0: report += f"🏎 Конверт «Драйв»: **{r_drive:,.0f} ₽**\n"
        if r_clothes > 0: report += f"👔 Конверт «Гардероб» (Шмотки): **{r_clothes:,.0f} ₽**\n"
        if r_holidays > 0: report += f"🎉 Фонд праздников: **{r_holidays:,.0f} ₽**\n"
        if r_health > 0: report += f"🩺 Конверт «Здоровье»: **{r_health:,.0f} ₽**\n"
        if r_auto > 0: report += f"🚗 Автофонд: **{r_auto:,.0f} ₽**\n"
        if r_masya_school > 0: report += f"🎒 Мася школа: **{r_masya_school:,.0f} ₽**\n"
        if r_monuments > 0: report += f"🪦 Конверт «Памятники»: **{r_monuments:,.0f} ₽**\n"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📝 Подтвердить и записать доход", callback_data=f"sm_{income}"))
        bot.send_message(message.chat.id, report, reply_markup=markup, parse_mode='Markdown')
    except Exception as e:
        logging.error(f"Ошибка основного дохода: {e}")
        bot.send_message(message.chat.id, "❌ Произошла ошибка расчетов.")

@bot.message_handler(func=lambda m: m.text == "🚀 Подработка")
def ask_side(message):
    msg = bot.send_message(message.chat.id, "🚀 Введите сумму случайной подработки:")
    bot.register_next_step_handler(msg, process_side)

def process_side(message):
    if message.text in ["💵 Основной доход", "🚀 Подработка", "📊 Ежемесячный отчет"]: return
    try:
        e2 = validate_amount(message.text)
        if e2 is None:
            bot.send_message(message.chat.id, "❌ **Ошибка ввода!** Введите число.")
            return

        level_name, r_pocket, r_drive, r_school, r_holidays, r_clothes, r_auto = calculate_side_distribution(e2)

        report = (
            f"🚀 **РАСЧЕТ ПОДРАБОТКИ ({e2:,.0f} ₽)**\n"
            f"⚡ Уровень дохода: `{level_name}`\n\n"
            f"🗂 **В твои конверты:**\n"
        )
        if r_pocket > 0: report += f"🛍 Конверт «Карман»: **{r_pocket:,.0f} ₽**\n"
        if r_drive > 0: report += f"🏎 Конверт «Драйв»: **{r_drive:,.0f} ₽**\n"
        if r_clothes > 0: report += f"👔 Конверт «Гардероб» (Шмотки): **{r_clothes:,.0f} ₽**\n"
        if r_school > 0: report += f"🎒 Конверт «Мася школа»: **{r_school:,.0f} ₽**\n"
        if r_holidays > 0: report += f"🎉 Фонд праздников: **{r_holidays:,.0f} ₽**\n"
        if r_auto > 0: report += f"🚗 Автофонд: **{r_auto:,.0f} ₽**\n"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📝 Подтвердить и записать доход", callback_data=f"ss_{e2}"))
        bot.send_message(message.chat.id, report, reply_markup=markup, parse_mode='Markdown')
    except Exception as e:
        logging.error(f"Ошибка подработки: {e}")
        bot.send_message(message.chat.id, "❌ Ошибка подработки.")

@bot.message_handler(func=lambda m: m.text == "📊 Ежемесячный отчет")
def show_monthly_report(message):
    now = datetime.now()
    current_month = now.strftime("%Y-%m")
    prev_month = f"{now.year - 1}-12" if now.month == 1 else f"{now.year}-{now.month - 1:02d}"
    
    total_main = total_side = total_prev = 0.0
    r_pocket = r_drive = r_school = r_holidays = r_health = r_auto = r_monuments = r_clothes = 0.0
    
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("|")
                if len(parts) < 4: continue
                if parts[0] == prev_month: total_prev += float(parts[3])
                if parts[0] == current_month:
                    if parts[2] == "основной": total_main += float(parts[3])
                    else: total_side += float(parts[3])
                    r_pocket += float(parts[4]) if len(parts) > 4 else 0.0
                    r_drive += float(parts[5]) if len(parts) > 5 else 0.0
                    r_school += float(parts[6]) if len(parts) > 6 else 0.0
                    r_holidays += float(parts[8]) if len(parts) > 8 else 0.0
                    r_health += float(parts[9]) if len(parts) > 9 else 0.0
                    r_auto += float(parts[10]) if len(parts) > 10 else 0.0
                    r_monuments += float(parts[11]) if len(parts) > 11 else 0.0
                    r_clothes += float(parts[13]) if len(parts) > 13 else 0.0
                        
    total_earned = total_main + total_side
    msg = (
        f"📊 **ФИНАНСОВЫЙ ОТЧЕТ**\n📅 Период: `{current_month}`\n═══════════════════════════\n\n"
        f"📈 **ДВИЖЕНИЕ КАПИТАЛА:**\n├ Всего вошло: **{total_earned:,.2f} ₽**\n"
        f"├ Основной: {total_main:,.2f} ₽\n└ Подработки: {total_side:,.2f} ₽\n\n"
        f"🛡️ **БЕЗОПАСНОСТЬ:**\n"
    )
    if r_school > 0: msg += f"├ 🎒 Мася школа: {r_school:,.0f} ₽\n"
    if r_auto > 0: msg += f"├ 🚗 Автофонд: {r_auto:,.0f} ₽\n"
    if r_health > 0: msg += f"├ 🩺 Здоровье: {r_health:,.0f} ₽\n"
    if r_monuments > 0: msg += f"└ 🪦 Памятники: {r_monuments:,.0f} ₽\n"
    else: msg += "└ Конверты безопасности пусты\n"
    
    msg += f"\n🔥 **СВОБОДА И ЖИЗНЬ:**\n"
    if r_pocket > 0: msg += f"├ 🛍 Чистый Карман: {r_pocket:,.0f} ₽\n"
    if r_drive > 0: msg += f"├ 🏎 Конверт Драйв: {r_drive:,.0f} ₽\n"
    if r_clothes > 0: msg += f"├ 👔 Одежда: {r_clothes:,.0f} ₽\n"
    if r_holidays > 0: msg += f"└ 🎉 Фонд праздников: {r_holidays:,.0f} ₽\n"
    else: msg += "└ Конверты жизни пусты\n"
    
    msg += f"═══════════════════════════\n📅 **СРАВНЕНИЕ:**\n└ ⏪ Было в `{prev_month}`: **{total_prev:,.2f} ₽**"
    bot.send_message(message.chat.id, msg, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    try:
        parts = call.data.split("_")
        action = parts[0]
        amount = float(parts[1])

        if action == "sm":
            _, r_pocket, r_drive, r_school, r_holidays, r_health, r_auto, r_monuments, r_clothes = calculate_cash_distribution(amount)
            save_to_stats("основной", amount, r_pocket, r_drive, r_school, 0.0, r_holidays, r_health, r_auto, r_monuments, 0.0, r_clothes)
            bot.answer_callback_query(call.id, "Доход успешно зафиксирован!")
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=call.message.text + "\n\n✅ **ДОХОД ПОДТВЕРЖДЕН И ЗАПИСАН**", parse_mode='Markdown')
            
        elif action == "ss":
            _, r_pocket, r_drive, r_school, r_holidays, r_clothes, r_auto = calculate_side_distribution(amount)
            save_to_stats("подработка", amount, r_pocket, r_drive, r_school, 0.0, r_holidays, 0.0, r_auto, 0.0, 0.0, r_clothes)
            bot.answer_callback_query(call.id, "Запись обновлена!")
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=call.message.text + "\n\n✅ **ПОДРАБОТКА ПОДТВЕРЖДЕНА И ЗАПИСАНА**", parse_mode='Markdown')
    except Exception as e:
        logging.error(f"Ошибка в callback: {e}")
        bot.answer_callback_query(call.id, "❌ Ошибка подтверждения")

app = Flask('')
@app.route('/')
def home(): return "Финансовый движок активен!"

def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    bot.infinity_polling()
