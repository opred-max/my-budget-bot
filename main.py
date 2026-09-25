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
        "👋 **Financial Engine v3.5 активирован.**\n"
        "Успешно внедрены: фиксированные 60% супруге, умное округление до 10 ₽ "
        "и автоматическое слияние Стабфонда с Подушкой безопасности.\n\n"
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
        f"📅 План трат на текущий месяц: **{month_target:,.0f} ₽**\n"
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
            msg = bot.send_message(message.chat.id, "❌ **Ошибка ввода!** Введите корректное положительное число (например, 45000):")
            bot.register_next_step_handler(msg, process_cash)
            return

        # Новое железное правило семейного бюджета
        wife_cash = income * 0.60
        c7 = income * 0.40
        
        current_month = datetime.now().month
        holiday_target_this_month = HOLIDAYS_CALENDAR.get(current_month, 0)
        
        pocket, drive, holidays, health, auto, cushion, monuments, masya_school = [0.0]*8
        mode_name = ""
        
        if c7 < 31416:
            if c7 < 14750:
                mode_name = "🟥 Антикризисный режим"
                # Проверяем, есть ли траты на праздники в этом месяце. Если нет — отдаем долю Подушке
                p_holidays = 0.16 if holiday_target_this_month > 0 else 0.0
                p_cushion = 0.06 + (0.16 if holiday_target_this_month == 0 else 0.0)
                
                pocket = c7 * 0.30
                drive = c7 * 0.22
                holidays = c7 * p_holidays
                health = c7 * 0.12
                auto = c7 * 0.10
                cushion = c7 * p_cushion
                monuments = c7 * 0.04
            else:
                mode_name = "🟨 Переходный режим «Гарант»"
                pocket = 10000.0
                drive = min(3000.0, c7 - 10000.0)
                leftover = max(0.0, c7 - 13000.0)
                
                p_holidays = 0.30 if holiday_target_this_month > 0 else 0.0
                p_cushion = 0.12 + (0.30 if holiday_target_this_month == 0 else 0.0)
                
                holidays = min(5750.0, leftover * p_holidays)
                # Если лимит праздников усечен из-за min(), разницу тоже отдадим в подушку позже
                unused_holidays_share = (leftover * 0.30) - holidays if holiday_target_this_month > 0 else 0.0
                
                health = min(2000.0, leftover * 0.23)
                auto = min(5000.0, leftover * 0.20)
                cushion = (leftover * p_cushion) + unused_holidays_share
                masya_school = leftover * 0.10
                monuments = min(2000.0, leftover * 0.05)
                
                total_allocated = pocket + drive + holidays + health + auto + cushion + masya_school + monuments
                if total_allocated < c7:
                    pocket += (c7 - total_allocated)

            # ПРИМЕНЕНИЕ УМНОГО ОКРУГЛЕНИЯ ДО 10 РУБЛЕЙ
            r_pocket = math.floor(pocket / 10) * 10
            r_drive = math.floor(drive / 10) * 10
            r_holidays = math.floor(holidays / 10) * 10
            r_health = math.floor(health / 10) * 10
            r_auto = math.floor(auto / 10) * 10
            r_monuments = math.floor(monuments / 10) * 10
            r_masya_school = math.floor(masya_school / 10) * 10
            
            # Все «хвосты» округлений суммируются и направляются в Подушку безопасности
            allocated_except_cushion = r_pocket + r_drive + r_holidays + r_health + r_auto + r_monuments + r_masya_school
            r_cushion = c7 - allocated_except_cushion

            report = (
                f"📊 **РАСЧЕТ ОСНОВНОГО ДОХОДА ({income:,.0f} ₽)**\n"
                f"⚙️ Режим твоей доли: `{mode_name}`\n\n"
                f"💵 **Наличные (От продаж):**\n"
                f"└ 👩 Жене наличными (60%): **{wife_cash:,.0f} ₽**\n"
                f"└ 🧔 Твоя чистая доля (40%): **{c7:,.0f} ₽**\n\n"
                f"🗂 **Распределение по конвертам (округлено до 10 ₽):**\n"
                f"🛍 Конверт «Карман»: **{r_pocket:,.0f} ₽**\n"
                f"🏎 Конверт «Драйв»: **{r_drive:,.0f} ₽**\n"
                f"🎉 Фонд праздников: **{r_holidays:,.0f} ₽**\n"
                f"🩺 Конверт «Здоровье»: **{r_health:,.0f} ₽**\n"
                f"🚗 Автофонд: **{r_auto:,.0f} ₽**\n"
                f"🎒 Мася школа: **{r_masya_school:,.0f} ₽**\n"
                f"🪦 Конверт «Памятники»: **{r_monuments:,.0f} ₽**\n"
                f"🏦 Конверт «Подушка» (+остатки): **{r_cushion:,.0f} ₽** 🔥"
            )
            bot.send_message(message.chat.id, report, parse_mode='Markdown')

        else:
            mode_name = "♾ Градиентный Жирный режим"
            
            holidays_raw = 5750.0 if holiday_target_this_month > 0 else 0.0
            health = 2000.0
            auto = 5000.0
            monuments = 2000.0
            
            # Стабфонд ликвидирован, его 15% уходят напрямую в Подушку безопасности
            cushion_raw_share = (c7 - 14750.0) * 0.15 
            free_remainder = (c7 - 14750.0) * 0.85
            
            masya_school = free_remainder * 0.10
            personal_pool = free_remainder * 0.90
            
            pocket_raw = personal_pool * 0.60
            drive_raw = 3000.0 + (personal_pool * 0.20)
            cushion_from_pool = personal_pool * 0.20
            
            cushion = cushion_raw_share + cushion_from_pool
            if holiday_target_this_month == 0:
                cushion += 5750.0 # Праздники текущего месяца также ушли в подушку
                
            holidays = holidays_raw

            target_floor = 15000.0
            if pocket_raw < target_floor:
                pocket_deficit = target_floor - pocket_raw
                buffer_pool = drive_raw + cushion_raw_share
                if buffer_pool > 0:
                    extract_factor = min(1.0, pocket_deficit / buffer_pool)
                    allocated_from_buffer = buffer_pool * extract_factor
                    
                    share_drive = drive_raw / buffer_pool
                    share_cushion = cushion_raw_share / buffer_pool
                    
                    drive = drive_raw - (allocated_from_buffer * share_drive)
                    cushion -= (allocated_from_buffer * share_cushion)
                    pocket = pocket_raw + allocated_from_buffer
                else:
                    drive, pocket = drive_raw, pocket_raw
            else:
                bonus_factor = 0.15 * (1.0 - math.exp(-(pocket_raw - target_floor)/20000.0))
                pocket = pocket_raw + (cushion_raw_share * bonus_factor)
                cushion -= (cushion_raw_share * bonus_factor)
                drive = drive_raw

            # ПРИМЕНЕНИЕ УМНОГО ОКРУГЛЕНИЯ ДО 10 РУБЛЕЙ
            r_pocket = math.floor(pocket / 10) * 10
            r_drive = math.floor(drive / 10) * 10
            r_holidays = math.floor(holidays / 10) * 10
            r_health = math.floor(health / 10) * 10
            r_auto = math.floor(auto / 10) * 10
            r_monuments = math.floor(monuments / 10) * 10
            r_masya_school = math.floor(masya_school / 10) * 10
            
            # Все «хвосты» округлений уходят в Подушку
            allocated_except_cushion = r_pocket + r_drive + r_holidays + r_health + r_auto + r_monuments + r_masya_school
            r_cushion = c7 - allocated_except_cushion

            report = (
                f"📊 **РАСЧЕТ ОСНОВНОГО ДОХОДА ({income:,.0f} ₽)**\n"
                f"⚙️ Режим твоей доли: `{mode_name}`\n\n"
                f"💵 **Наличные (От продаж):**\n"
                f"└ 👩 Жене наличными (60%): **{wife_cash:,.0f} ₽**\n"
                f"└ 🧔 Твоя чистая доля (40%): **{c7:,.0f} ₽**\n\n"
                f"🗂 **Распределение по твоим конвертам (округлено до 10 ₽):**\n"
                f"🛍 Конверт «Карман» (каскад): **{r_pocket:,.0f} ₽**\n"
                f"🏎 Конверт «Драйв» (динамика): **{r_drive:,.0f} ₽**\n"
                f"🎉 Фонд праздников: **{r_holidays:,.0f} ₽**\n"
                f"🩺 Конверт «Здоровье»: **{r_health:,.0f} ₽**\n"
                f"🚗 Автофонд: **{r_auto:,.0f} ₽**\n"
                f"🎒 Мася школа: **{r_masya_school:,.0f} ₽**\n"
                f"🪦 Конверт «Памятники»: **{r_monuments:,.0f} ₽**\n"
                f"🏦 Конверт «Подушка» (+Сверхкапитал и хвосты): **{r_cushion:,.0f} ₽** 🔥"
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
        
        pocket, drive, credit, school, holidays, cushion = [0.0] * 6
        
        # РАСЧЕТ КОЭФФИЦИЕНТОВ (Везде сумма строго равна 1.00)
        if e2 <= 2000:
            level_name = "🌱 Микро (до 2к)"
            # Стабфонд перенесен в Подушку. Досрочка кредита и Подушка возвращены в строй.
            p_pocket, p_drive, p_credit, p_school, p_holidays, p_cushion = 0.45, 0.15, 0.25, 0.10, 0.00, 0.05
        elif e2 <= 5000:
            level_name = "📈 Стандарт (2к - 5к)"
            # Бывший 1% Стабфонда объединен с Подушкой (стало 0.04)
            p_pocket, p_drive, p_credit, p_school, p_holidays, p_cushion = 0.43, 0.15, 0.25, 0.10, 0.03, 0.04
        elif e2 <= 8000:
            level_name = "🚀 Профи (5к - 8к)"
            # Бывшие 2% Стабфонда объединены с Подушкой (стало 0.05)
            p_pocket, p_drive, p_credit, p_school, p_holidays, p_cushion = 0.45, 0.15, 0.25, 0.12, 0.03, 0.05
        else:
            level_name = "🔥 Турбо-Досрочка (Выше 8к)"
            # Бывшие 2% Стабфонда объединены с Подушкой (стало 0.05)
            p_pocket, p_drive, p_credit, p_school, p_holidays, p_cushion = 0.50, 0.15, 0.20, 0.12, 0.03, 0.05

        pocket = e2 * p_pocket
        drive = e2 * p_drive
        credit = e2 * p_credit
        school = e2 * p_school
        holidays = e2 * p_holidays
        cushion = e2 * p_cushion

        # ПРИМЕНЕНИЕ УМНОГО ОКРУГЛЕНИЯ ДО 10 РУБЛЕЙ
        r_pocket = math.floor(pocket / 10) * 10
        r_drive = math.floor(drive / 10) * 10
        r_school = math.floor(school / 10) * 10
        r_holidays = math.floor(holidays / 10) * 10
        
        # Распределяем остатки округления в зависимости от наличия кредита в режиме
        if p_credit > 0:
            r_cushion = math.floor(cushion / 10) * 10
            allocated_except_credit = r_pocket + r_drive + r_school + r_holidays + r_cushion
            r_credit = e2 - allocated_except_credit  # Сюда падают все хвосты округления
        else:
            r_credit = 0
            allocated_except_cushion = r_pocket + r_drive + r_school + r_holidays
            r_cushion = e2 - allocated_except_cushion  # Если кредита нет (например, кастомный режим), хвосты идут в подушку

        report = (
            f"🚀 **РАСЧЕТ ПОДРАБОТКИ ({e2:,.0f} ₽)**\n"
            f"⚡ Уровень дохода: `{level_name}`\n\n"
        )
        
        if r_credit > 0:
            report += f"📉 **ДОСРОЧКА КРЕДИТА (+остатки округления):** **{r_credit:,.0f} ₽** 🔥\n\n"

        report += (
            f"🗂 **В твои конверты (округлено до 10 ₽):**\n"
            f"🛍 Конверт «Карман»: **{r_pocket:,.0f} ₽**\n"
            f"🏎 Конверт «Драйв»: **{r_drive:,.0f} ₽**\n"
            f"🎒 Конверт «Мася школа»: **{r_school:,.0f} ₽**\n"
            f"🏦 Конверт «Подушка»: **{r_cushion:,.0f} ₽**\n"
        )
        
        if r_holidays > 0: 
            report += f"🎉 Фонд праздников: **{r_holidays:,.0f} ₽**\n"
        
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
