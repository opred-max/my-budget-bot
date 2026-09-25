import telebot
from telebot import types
import os
from datetime import datetime
import math
from flask import Flask
import threading

# =====================================================================
# ТОКЕН БОТА И НАСТРОЙКИ
# =====================================================================
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
bot = telebot.TeleBot(TOKEN)

DETAILED_HOLIDAYS = [
    {"date": "05.01", "name": "Теща", "amount": 2000},
    {"date": "14.01", "name": "Настя", "amount": 5000},
    {"date": "08.03", "name": "Женский день", "amount": 10000},
    {"date": "22.03", "name": "Паша", "amount": 2000},
    {"date": "15.04", "name": "Шеф", "amount": 3000},
    {"date": "29.04", "name": "Иван Федорович", "amount": 2000},
    {"date": "06.05", "name": "Сестра", "amount": 2000},
    {"date": "27.07", "name": "Племянница", "amount": 1000},
    {"date": "15.08", "name": "Годовщина", "amount": 5000},
    {"date": "20.08", "name": "Жена", "amount": 15000},
    {"date": "31.08", "name": "Жанна", "amount": 3000},
    {"date": "27.09", "name": "Маша", "amount": 3000},
    {"date": "07.10", "name": "Мама", "amount": 2000},
    {"date": "16.10", "name": "Мася", "amount": 5000},
    {"date": "21.10", "name": "Племянница", "amount": 1000},
    {"date": "31.12", "name": "Новый Год", "amount": 10000}
]

HOLIDAYS_CALENDAR = {
    1: 7000, 2: 0, 3: 12000, 4: 5000, 5: 2000, 6: 0,
    7: 1000, 8: 23000, 9: 3000, 10: 8000, 11: 0, 12: 10000
}
def validate_amount(text):
    try:
        val = float(text.strip().replace(',', '.'))
        if val <= 0:
            return None
        return val
    except ValueError:
        return None

def get_main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_cash = types.KeyboardButton("💵 Основной доход")
    btn_side = types.KeyboardButton("🚀 Подработка")
    btn_status = types.KeyboardButton("ℹ️ Календарь расходов")
    keyboard.add(btn_cash, btn_side)
    keyboard.add(btn_status)
    return keyboard

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "👋 **Financial Engine v3.0 активирован.**\n"
        "Внедрен гибкий каскадно-градиентный алгоритм распределения долей.\n\n"
        "Используй кнопки меню для мгновенного расчета доходов 👇"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard(), parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "ℹ️ Календарь расходов")
def show_balances(message):
    current_month = datetime.now().month
    current_year = datetime.now().year
    month_target = HOLIDAYS_CALENDAR.get(current_month, 0)
    
    upcoming_alerts = []
    today = datetime.now().date()
    
    for item in DETAILED_HOLIDAYS:
        day, month = map(int, item["date"].split('.'))
        event_date = datetime(current_year, month, day).date()
        if event_date < today:
            event_date = datetime(current_year + 1, month, day).date()
            
        days_left = (event_date - today).days
        if 0 <= days_left <= 7:
            if days_left == 0:
                upcoming_alerts.append(f"🚨 **СЕГОДНЯ:** {item['name']} — нужно **{item['amount']:,.0f} ₽**!")
            else:
                upcoming_alerts.append(f"⚠️ **Через {days_left} дн.:** {item['name']} ({item['date']}) — план **{item['amount']:,.0f} ₽**")

    msg = (
        f"ℹ️ **ИНФОРМАЦИЯ О РАСХОДАХ:**\n\n"
        f"📅 План расходов на текущий месяц: **{month_target:,.2f} ₽**\n"
    )
    if upcoming_alerts:
        msg += "\n🔔 **НАДВИГАЮЩИЕСЯ СОБЫТИЯ:**\n" + "\n".join(upcoming_alerts)
        
    bot.send_message(message.chat.id, msg, parse_mode='Markdown')
# =====================================================================
# ЛОГИКА ОБРАБОТКИ ВВОДА ОСНОВНОГО ДОХОДА
# =====================================================================
@bot.message_handler(func=lambda m: m.text == "💵 Основной доход")
def ask_cash(message):
    msg = bot.send_message(message.chat.id, "💵 Отлично! Введите общую сумму наличных от продаж:")
    bot.register_next_step_handler(msg, process_cash)

def process_cash(message):
    try:
        income = validate_amount(message.text)
        if income is None:
            msg = bot.send_message(message.chat.id, "❌ **Ошибка ввода!** Пожалуйста, введите корректное положительное число (например, 45000):")
            bot.register_next_step_handler(msg, process_cash)
            return

        wife_cash = max(50000.0, income * 0.6)
        c7 = max(0.0, income - wife_cash)
        
        current_month = datetime.now().month
        holiday_target_this_month = HOLIDAYS_CALENDAR.get(current_month, 0)
        
        pocket, drive, holidays, health, auto, cushion, monuments, masya_school, stabfond = [0.0]*9
        mode_name = ""
        
        if c7 < 31416:
            if c7 < 14750:
                mode_name = "🟥 Антикризисный режим"
                pocket = c7 * 0.30
                drive = c7 * 0.22
                holidays = c7 * 0.16
                health = c7 * 0.12
                auto = c7 * 0.10
                cushion = c7 * 0.06
                monuments = c7 * 0.04
            else:
                mode_name = "🟨 Переходный режим «Гарант»"
                pocket = 10000.0
                drive = min(3000.0, c7 - 10000.0)
                leftover = max(0.0, c7 - 13000.0)
                
                holidays = min(5750.0, leftover * 0.30)
                health = min(2000.0, leftover * 0.23)
                auto = min(5000.0, leftover * 0.20)
                cushion = leftover * 0.12
                masya_school = leftover * 0.10
                monuments = min(2000.0, leftover * 0.05)
                
                total_allocated = pocket + drive + holidays + health + auto + cushion + masya_school + monuments
                if total_allocated < c7:
                    pocket += (c7 - total_allocated)

            report = (
                f"📊 **РАСЧЕТ ОСНОВНОГО ДОХОДА ({income:,.0f} ₽)**\n"
                f"⚙️ Режим твоей доли: `{mode_name}`\n\n"
                f"💵 **Наличные (От продаж):**\n"
                f"└ 👩 Жене наличными: **{wife_cash:,.0f} ₽**\n"
                f"└ 🧔 Твоя чистая доля: **{c7:,.0f} ₽**\n\n"
                f"🗂 **Распределение по конвертам:**\n"
                f"🛍 Конверт «Карман»: **{pocket:,.0f} ₽**\n"
                f"🏎 Конверт «Драйв»: **{drive:,.0f} ₽**\n"
                f"🎉 Фонд праздников: **{holidays:,.0f} ₽**\n"
                f"🩺 Конверт «Здоровье»: **{health:,.0f} ₽**\n"
                f"🚗 Автофонд: **{auto:,.0f} ₽**\n"
                f"🎒 Мася школа: **{masya_school:,.0f} ₽**\n"
                f"🏦 Конверт «Подушка»: **{cushion:,.0f} ₽**\n"
                f"🪦 Конверт «Памятники»: **{monuments:,.0f} ₽**"
            )
            bot.send_message(message.chat.id, report, parse_mode='Markdown')

        else:
            mode_name = "♾ Градиентный Жирный режим"
            wife_cash = income * 0.60
            c7 = income * 0.40
            
            holidays = 5750.0
            health = 2000.0
            auto = 5000.0
            monuments = 2000.0
            
            stabfond_raw = (c7 - 14750.0) * 0.15
            free_remainder = (c7 - 14750.0) * 0.85
            
            masya_school = free_remainder * 0.10
            personal_pool = free_remainder * 0.90
            
            pocket_raw = personal_pool * 0.60
            drive_raw = 3000.0 + (personal_pool * 0.20)
            cushion = personal_pool * 0.20
            
            target_floor = 15000.0
            if pocket_raw < target_floor:
                pocket_deficit = target_floor - pocket_raw
                buffer_pool = drive_raw + stabfond_raw
                if buffer_pool > 0:
                    extract_factor = min(1.0, pocket_deficit / buffer_pool)
                    allocated_from_buffer = buffer_pool * extract_factor
                    
                    share_drive = drive_raw / buffer_pool
                    share_stab = stabfond_raw / buffer_pool
                    
                    drive = drive_raw - (allocated_from_buffer * share_drive)
                    stabfond = stabfond_raw - (allocated_from_buffer * share_stab)
                    pocket = pocket_raw + allocated_from_buffer
                else:
                    drive, stabfond, pocket = drive_raw, stabfond_raw, pocket_raw
            else:
                bonus_factor = 0.15 * (1.0 - math.exp(-(pocket_raw - target_floor)/20000.0))
                pocket = pocket_raw + (stabfond_raw * bonus_factor)
                stabfond = stabfond_raw * (1.0 - bonus_factor)
                drive = drive_raw

            if wife_cash < 55000.0:
                deficit_wife = 55000.0 - wife_cash
                deduct_monuments = min(deficit_wife, monuments)
                monuments -= deduct_monuments
                rem_deficit = deficit_wife - deduct_monuments
                
                if rem_deficit > 0:
                    sum_funds = auto + holidays + stabfond + cushion + health
                    if sum_funds > 0:
                        auto -= rem_deficit * (auto / sum_funds)
                        holidays -= rem_deficit * (holidays / sum_funds)
                        stabfond -= rem_deficit * (stabfond / sum_funds)
                        cushion -= rem_deficit * (cushion / sum_funds)
                        health -= rem_deficit * (health / sum_funds)
                wife_cash = 55000.0

            report = (
                f"📊 **РАСЧЕТ ОСНОВНОГО ДОХОДА ({income:,.0f} ₽)**\n"
                f"⚙️ Режим твоей доли: `{mode_name}`\n\n"
                f"💵 **Наличные (От продаж):**\n"
                f"└ 👩 Жене наличными (60%): **{wife_cash:,.0f} ₽**\n"
                f"└ 🧔 Твоя чистая доля (40%): **{c7:,.0f} ₽**\n\n"
                f"🗂 **Распределение по твоим конвертам:**\n"
                f"🛍 Конверт «Карман» (каскад): **{pocket:,.0f} ₽**\n"
                f"🏎 Конверт «Драйв» (динамика): **{drive:,.0f} ₽**\n"
                f"🎉 Фонд праздников: **{holidays:,.0f} ₽**\n"
                f"🩺 Конверт «Здоровье»: **{health:,.0f} ₽**\n"
                f"🚗 Автофонд: **{auto:,.0f} ₽**\n"
                f"🎒 Мася школа: **{masya_school:,.0f} ₽**\n"
                f"🏦 Конверт «Подушка»: **{cushion:,.0f} ₽**\n"
                f"🪦 Конверт «Памятники»: **{monuments:,.0f} ₽**\n"
                f"🛡️ Резерв («Стабфонд» схемы): **{stabfond:,.0f} ₽**"
            )
            bot.send_message(message.chat.id, report, parse_mode='Markdown')
            
    except Exception as e:
        bot.send_message(message.chat.id, "❌ Произошла непредвиденная ошибка расчетов основного дохода.")
# =====================================================================
# БЛОК ПОДРАБОТОК И ЗАПУСК СЕРВИСА
# =====================================================================
@bot.message_handler(func=lambda m: m.text == "🚀 Подработка")
def ask_side(message):
    msg = bot.send_message(message.chat.id, "🚀 Отлично! Введите сумму случайной подработки:")
    bot.register_next_step_handler(msg, process_side)

def process_side(message):
    try:
        e2 = validate_amount(message.text)
        if e2 is None:
            msg = bot.send_message(message.chat.id, "❌ **Ошибка ввода!** Пожалуйста, введите положительное число для подработки:")
            bot.register_next_step_handler(msg, process_side)
            return
        
        pocket, drive, credit, school, holidays, cushion, stab = [0.0] * 7
        
        # РАСЧЕТ КОЭФФИЦИЕНТОВ (Везде сумма строго равна 1.00)
        if e2 <= 2000:
            level_name = "🌱 Микро (до 2к)"
            # ИСПРАВЛЕНО: Кредит, праздники, подушка и стаб ушли под нож. Суммы теперь крупные.
            p_pocket, p_drive, p_credit, p_school, p_holidays, p_cushion, p_stab = 0.70, 0.20, 0.00, 0.10, 0.00, 0.00, 0.00
        elif e2 <= 5000:
            level_name = "📈 Стандарт (2к - 5к)"
            p_pocket, p_drive, p_credit, p_school, p_holidays, p_cushion, p_stab = 0.43, 0.15, 0.25, 0.10, 0.03, 0.03, 0.01
        elif e2 <= 8000:
            level_name = "🚀 Профи (5к - 8к)"
            p_pocket, p_drive, p_credit, p_school, p_holidays, p_cushion, p_stab = 0.45, 0.15, 0.25, 0.12, 0.03, 0.03, 0.02
        else:
            level_name = "🔥 Турбо-Досрочка (Выше 8к)"
            p_pocket, p_drive, p_credit, p_school, p_holidays, p_cushion, p_stab = 0.50, 0.15, 0.20, 0.12, 0.03, 0.03, 0.02

        pocket = e2 * p_pocket
        drive = e2 * p_drive
        credit = e2 * p_credit
        school = e2 * p_school
        holidays = e2 * p_holidays
        cushion = e2 * p_cushion
        stab = e2 * p_stab

        report = (
            f"🚀 **РАСЧЕТ ПОДРАБОТКИ ({e2:,.0f} ₽)**\n"
            f"⚡ Уровень дохода: `{level_name}`\n\n"
        )
        
        if credit > 0:
            report += f"📉 **ДОСРОЧКА КРЕДИТА:** **{credit:,.0f} ₽** 🔥\n\n"

        report += (
            f"🗂 **В твои конверты:**\n"
            f"🛍 Конверт «Карман»: **{pocket:,.0f} ₽**\n"
            f"🏎 Конверт «Драйв»: **{drive:,.0f} ₽**\n"
            f"🎒 Конверт «Мася школа»: **{school:,.0f} ₽**\n"
        )
        
        if holidays > 0: report += f"🎉 Фонд праздников: **{holidays:,.0f} ₽**\n"
        if cushion > 0: report += f"🏦 Конверт «Подушка»: **{cushion:,.0f} ₽**\n"
        if stab > 0: report += f"🛡️ Резерв («Стабфонд» подработок): **{stab:,.0f} ₽**"
        
        bot.send_message(message.chat.id, report, parse_mode='Markdown')
        
    except:
        bot.send_message(message.chat.id, "❌ Произошла ошибка обработки подработки.")

# =====================================================================
# МАСКИРОВКА ПОД ВЕБ-СЕРВИС ДЛЯ RENDER
# =====================================================================
app = Flask('')

@app.route('/')
def home():
    return "Бот полностью настроен, очищен от копилок и работает!"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    bot.infinity_polling()
