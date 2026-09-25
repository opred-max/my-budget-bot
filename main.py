import telebot
from telebot import types
import os
from datetime import datetime
import math
from flask import Flask
import threading

# =====================================================================
# ТОКЕН БОТА И НАСТРОЙКИ ФАЙЛОВ
# =====================================================================
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
bot = telebot.TeleBot(TOKEN)

STATS_FILE = "monthly_stats.txt"
BALANCES_FILE = "balances.txt"

# Календарь плановых расходов по месяцам
HOLIDAYS_CALENDAR = {
    1: 7000, 2: 0, 3: 12000, 4: 5000, 5: 2000, 6: 0,
    7: 1000, 8: 23000, 9: 3000, 10: 8000, 11: 0, 12: 10000
}

# =====================================================================
# ФУНКЦИИ СИСТЕМЫ ХРАНЕНИЯ ДАННЫХ
# =====================================================================
def load_balances():
    """Загружает текущие остатки Кредита и Подушки"""
    # Стартовые значения по умолчанию
    default_balances = {"credit": 125423.45, "cushion_accumulated": 0.0}
    if not os.path.exists(BALANCES_FILE):
        return default_balances
    try:
        with open(BALANCES_FILE, "r", encoding="utf-8") as f:
            data = f.read().strip().split("|")
            return {
                "credit": max(0.0, float(data[0])),
                "cushion_accumulated": max(0.0, float(data[1]))
            }
    except:
        return default_balances

def save_balances(credit, cushion):
    """Сохраняет текущие остатки Кредита и Подушки"""
    with open(BALANCES_FILE, "w", encoding="utf-8") as f:
        f.write(f"{credit:.2f}|{cushion:.2f}")

def save_to_stats(income_type, total, pocket, drive, school, cushion, holidays=0, health=0, auto=0, monuments=0, credit=0):
    """Записывает подтвержденный доход в файл статистики текущего месяца"""
    month_key = datetime.now().strftime("%Y-%m")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    row = (
        f"{month_key}|{timestamp}|{income_type}|{total:.2f}|{pocket:.2f}|{drive:.2f}|"
        f"{school:.2f}|{cushion:.2f}|{holidays:.2f}|{health:.2f}|{auto:.2f}|{monuments:.2f}|{credit:.2f}\n"
    )
    with open(STATS_FILE, "a", encoding="utf-8") as f:
        f.write(row)
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
    btn_report = types.KeyboardButton("📊 Ежемесячный отчет")
    btn_status = types.KeyboardButton("⚙️ Мои Балансы и Цели")
    keyboard.add(btn_cash, btn_side)
    keyboard.add(btn_report, btn_status)
    return keyboard

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "👋 **Financial Engine v4.0 активирован.**\n"
        "Внедрено: 60% супруге, умное округление до 10 ₽, правила сверхдохода "
        "и автоконтроль лимитов кредита и подушки.\n\n"
        "Используй кнопки меню для мгновенного расчета 👇"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard(), parse_mode='Markdown')

# =====================================================================
# ЭКРАН МОИХ БАЛАНСОВ И ЦЕНТР СВОДКИ
# =====================================================================
@bot.message_handler(func=lambda m: m.text == "⚙️ Мои Балансы и Цели")
def show_balances(message):
    b = load_balances()
    msg = (
        f"⚙️ **ТЕКУЩЕЕ СОСТОЯНИЕ ЦЕЛЕЙ:**\n\n"
        f"📉 Остаток по Кредиту: **{b['credit']:,.2f} ₽**\n"
        f"🏦 Накоплено в Подушку: **{b['cushion_accumulated']:,.2f} ₽** / 100,000 ₽\n"
    )
    bot.send_message(message.chat.id, msg, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "📊 Ежемесячный отчет")
def show_monthly_report(message):
    current_month = datetime.now().strftime("%Y-%m")
    
    total_main, total_side, total_earned = 0.0, 0.0, 0.0
    r_pocket, r_drive, r_school, r_cushion, r_holidays, r_health, r_auto, r_monuments, r_credit = [0.0]*9
    
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("|")
                if len(parts) < 13: continue
                if parts[0] == current_month:
                    t_type = parts[2]
                    amt = float(parts[3])
                    if t_type == "основной": total_main += amt
                    else: total_side += amt
                    
                    r_pocket += float(parts[4])
                    r_drive += float(parts[5])
                    r_school += float(parts[6])
                    r_cushion += float(parts[7])
                    r_holidays += float(parts[8])
                    r_health += float(parts[9])
                    r_auto += float(parts[10])
                    r_monuments += float(parts[11])
                    r_credit += float(parts[12])
                    
    total_earned = total_main + total_side
    
    msg = (
        f"📊 **ФИНАНСОВАЯ СВОДКА ЗА ТЕКУЩИЙ МЕСЯЦ:**\n\n"
        f"💰 **Всего подтверждено: {total_earned:,.2f} ₽**\n"
        f" ├ Из основного дохода: {total_main:,.2f} ₽\n"
        f" └ Из подработок: {total_side:,.2f} ₽\n\n"
        f"🗂 **Распределено по конвертам за месяц:**\n"
        f"🛍 Карман: {r_pocket:,.0f} ₽\n"
        f"🏎 Драйв: {r_drive:,.0f} ₽\n"
        f"🎒 Мася школа: {r_school:,.0f} ₽\n"
        f"🏦 Подушка безопасности: {r_cushion:,.0f} ₽\n"
        f"📉 На досрочку кредита: {r_credit:,.0f} ₽\n"
        f"🎉 Фонд праздников: {r_holidays:,.0f} ₽\n"
        f"🩺 Здоровье: {r_health:,.0f} ₽\n"
        f"🚗 Автофонд: {r_auto:,.0f} ₽\n"
        f"🪦 Памятники: {r_monuments:,.0f} ₽"
    )
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

        b = load_balances()
        is_cushion_full = b["cushion_accumulated"] >= 100000.0

        wife_cash = income * 0.60
        c7 = income * 0.40
        
        current_month = datetime.now().month
        holiday_target_this_month = HOLIDAYS_CALENDAR.get(current_month, 0)
        
        pocket, drive, holidays, health, auto, cushion, monuments, masya_school = [0.0]*8
        mode_name = ""
        
        if c7 < 31416:
            if c7 < 14750:
                mode_name = "🟥 Антикризисный режим"
                p_holidays = 0.16 if holiday_target_this_month > 0 else 0.0
                p_cushion = 0.06 + (0.16 if holiday_target_this_month == 0 else 0.0)
                
                # Если подушка собрана, её доля уходит в Карман
                if is_cushion_full:
                    pocket = c7 * (0.30 + p_cushion)
                    cushion = 0.0
                else:
                    pocket = c7 * 0.30
                    cushion = c7 * p_cushion
                    
                drive = c7 * 0.22
                holidays = c7 * p_holidays
                health = c7 * 0.12
                auto = c7 * 0.10
                monuments = c7 * 0.04
            else:
                mode_name = "🟨 Переходный режим «Гарант»"
                pocket = 10000.0
                drive = min(3000.0, c7 - 10000.0)
                leftover = max(0.0, c7 - 13000.0)
                
                p_holidays = 0.30 if holiday_target_this_month > 0 else 0.0
                p_cushion = 0.12 + (0.30 if holiday_target_this_month == 0 else 0.0)
                
                holidays = min(5750.0, leftover * p_holidays)
                unused_holidays_share = (leftover * 0.30) - holidays if holiday_target_this_month > 0 else 0.0
                
                health = min(2000.0, leftover * 0.23)
                auto = min(5000.0, leftover * 0.20)
                masya_school = leftover * 0.10
                monuments = min(2000.0, leftover * 0.05)
                
                calculated_cushion = (leftover * p_cushion) + unused_holidays_share
                if is_cushion_full:
                    pocket += calculated_cushion
                    cushion = 0.0
                else:
                    cushion = calculated_cushion
                
                total_allocated = pocket + drive + holidays + health + auto + cushion + masya_school + monuments
                if total_allocated < c7:
                    pocket += (c7 - total_allocated)

            r_pocket = math.floor(pocket / 10) * 10
            r_drive = math.floor(drive / 10) * 10
            r_holidays = math.floor(holidays / 10) * 10
            r_health = math.floor(health / 10) * 10
            r_auto = math.floor(auto / 10) * 10
            r_monuments = math.floor(monuments / 10) * 10
            r_masya_school = math.floor(masya_school / 10) * 10
            
            allocated_except_cushion = r_pocket + r_drive + r_holidays + r_health + r_auto + r_monuments + r_masya_school
            
            if is_cushion_full:
                r_pocket += (c7 - allocated_except_cushion)
                r_cushion = 0.0
            else:
                r_cushion = c7 - allocated_except_cushion

        else:
            mode_name = "♾ Градиентный Жирный режим"
            holidays_raw = 5750.0 if holiday_target_this_month > 0 else 0.0
            health = 2000.0
            auto = 5000.0
            monuments = 2000.0
            
            cushion_raw_share = (c7 - 14750.0) * 0.15 
            free_remainder = (c7 - 14750.0) * 0.85
            
            masya_school = free_remainder * 0.10
            personal_pool = free_remainder * 0.90
            
            pocket_raw = personal_pool * 0.60
            drive_raw = 3000.0 + (personal_pool * 0.20)
            cushion_from_pool = personal_pool * 0.20
            
            cushion = cushion_raw_share + cushion_from_pool
            if holiday_target_this_month == 0:
                cushion += 5750.0
                
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

            if is_cushion_full:
                pocket += cushion
                cushion = 0.0

            r_pocket = math.floor(pocket / 10) * 10
            r_drive = math.floor(drive / 10) * 10
            r_holidays = math.floor(holidays / 10) * 10
            r_health = math.floor(health / 10) * 10
            r_auto = math.floor(auto / 10) * 10
            r_monuments = math.floor(monuments / 10) * 10
            r_masya_school = math.floor(masya_school / 10) * 10
            
            allocated_except_cushion = r_pocket + r_drive + r_holidays + r_health + r_auto + r_monuments + r_masya_school
            
            if is_cushion_full:
                r_pocket += (c7 - allocated_except_cushion)
                r_cushion = 0.0
            else:
                r_cushion = c7 - allocated_except_cushion

        report = (
            f"📊 **РАСЧЕТ ОСНОВНОГО ДОХОДА ({income:,.0f} ₽)**\n"
            f"⚙️ Режим твоей доли: `{mode_name}`\n\n"
            f"💵 **Наличные (От продаж):**\n"
            f"└ 👩 Жене наличными (60%): **{wife_cash:,.0f} ₽**\n"
            f"└ 🧔 Твоя чистая доля (40%): **{c7:,.0f} ₽**\n\n"
            f"🗂 **Распределение по конвертам:**\n"
            f"🛍 Конверт «Карман»: **{r_pocket:,.0f} ₽**\n"
            f"🏎 Конверт «Драйв»: **{r_drive:,.0f} ₽**\n"
            f"🎉 Фонд праздников: **{r_holidays:,.0f} ₽**\n"
            f"🩺 Конверт «Здоровье»: **{r_health:,.0f} ₽**\n"
            f"🚗 Автофонд: **{r_auto:,.0f} ₽**\n"
            f"🎒 Мася школа: **{r_masya_school:,.0f} ₽**\n"
            f"🪦 Конверт «Памятники»: **{r_monuments:,.0f} ₽**\n"
            f"🏦 Конверт «Подушка»: **{r_cushion:,.0f} ₽**"
        )
        
        markup = types.InlineKeyboardMarkup()
        cb_data = f"sub_main_{income}_{r_pocket}_{r_drive}_{r_masya_school}_{r_cushion}_{r_holidays}_{r_health}_{r_auto}_{r_monuments}"
        btn = types.InlineKeyboardButton("📝 Подтвердить и записать доход", callback_data=cb_data)
        markup.add(btn)
        
        bot.send_message(message.chat.id, report, reply_markup=markup, parse_mode='Markdown')
            
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
            msg = bot.send_message(message.chat.id, "❌ **Ошибка ввода!** Введите положительное число для подработки:")
            bot.register_next_step_handler(msg, process_side)
            return
        
        b = load_balances()
        is_credit_done = b["credit"] <= 0.0
        is_cushion_full = b["cushion_accumulated"] >= 100000.0

        pocket, drive, credit, school, holidays, cushion = [0.0] * 6
        
        # ПРАВИЛО №1: СВЕРХДОХОД (выше 10 000 ₽)
        if e2 > 10000:
            level_name = "🔥 Турбо Сверхдоход (Выше 10к)"
            pocket = 4500.0
            drive = 1500.0
            holidays = 0.0
            
            leftover = e2 - 6000.0
            # Школа забирает фиксированную долю из остатка
            school = leftover * 0.15
            rem_pool = leftover * 0.85
            
            if is_credit_done and is_cushion_full:
                pocket += rem_pool
            elif is_credit_done:
                cushion = rem_pool
            elif is_cushion_full:
                credit = rem_pool
            else:
                credit = rem_pool * 0.50
                cushion = rem_pool * 0.50
        else:
            # СТАНДАРТНЫЕ СЕТКИ С УЧЕТОМ ПРАВИЛА №4 (ЛИМИТЫ КРЕДИТА И ПОДУШКИ)
            if e2 <= 2000:
                level_name = "🌱 Микро (до 2к)"
                p_pocket, p_drive, p_credit, p_school, p_holidays, p_cushion = 0.45, 0.15, 0.25, 0.10, 0.00, 0.05
            elif e2 <= 5000:
                level_name = "📈 Стандарт (2к - 5к)"
                p_pocket, p_drive, p_credit, p_school, p_holidays, p_cushion = 0.43, 0.15, 0.25, 0.10, 0.03, 0.04
            else:
                level_name = "🚀 Профи (5к - 8к)"
                p_pocket, p_drive, p_credit, p_school, p_holidays, p_cushion = 0.45, 0.15, 0.25, 0.12, 0.03, 0.05

            # Перераспределение процентов, если цели закрыты
            if is_credit_done:
                p_cushion += p_credit
                p_credit = 0.0
            if is_cushion_full:
                p_pocket += p_cushion
                p_cushion = 0.0

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
        
        # Направление сдачи от округления
        if credit > 0:
            r_cushion = math.floor(cushion / 10) * 10
            allocated_except_credit = r_pocket + r_drive + r_school + r_holidays + r_cushion
            r_credit = e2 - allocated_except_credit
        else:
            r_credit = 0.0
            allocated_except_cushion = r_pocket + r_drive + r_school + r_holidays
            r_cushion = e2 - allocated_except_cushion

        report = (
            f"🚀 **РАСЧЕТ ПОДРАБОТКИ ({e2:,.0f} ₽)**\n"
            f"⚡ Уровень дохода: `{level_name}`\n\n"
        )
        if r_credit > 0:
            report += f"📉 **Досрочка кредита:** **{r_credit:,.0f} ₽** 🔥\n\n"

        report += (
            f"🗂 **В твои конверты:**\n"
            f"🛍 Конверт «Карман»: **{r_pocket:,.0f} ₽**\n"
            f"🏎 Конверт «Драйв»: **{r_drive:,.0f} ₽**\n"
            f"🎒 Конверт «Мася школа»: **{r_school:,.0f} ₽**\n"
            f"🏦 Конверт «Подушка»: **{r_cushion:,.0f} ₽**\n"
        )
        if r_holidays > 0: report += f"🎉 Фонд праздников: **{r_holidays:,.0f} ₽**\n"
        
        markup = types.InlineKeyboardMarkup()
        cb_data = f"sub_side_{e2}_{r_pocket}_{r_drive}_{r_school}_{r_cushion}_{r_holidays}_{r_credit}"
        btn = types.InlineKeyboardButton("📝 Подтвердить и записать доход", callback_data=cb_data)
        markup.add(btn)
        
        bot.send_message(message.chat.id, report, reply_markup=markup, parse_mode='Markdown')
        
    except:
        bot.send_message(message.chat.id, "❌ Произошла ошибка обработки подработки.")

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    try:
        if call.data.startswith("sub_main_"):
            p = call.data.split("_")
            income, r_pocket, r_drive, r_school, r_cushion, r_holidays, r_health, r_auto, r_monuments = map(float, p[2:])
            
            # Запись в статистику
            save_to_stats("основной", income, r_pocket, r_drive, r_school, r_cushion, r_holidays, r_health, r_auto, r_monuments, 0.0)
            
            # Обновление Подушки
            b = load_balances()
            b["cushion_accumulated"] += r_cushion
            save_balances(b["credit"], b["cushion_accumulated"])
            
            bot.answer_callback_query(call.id, "Доход успешно зафиксирован!")
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                                  text=call.message.text + "\n\n✅ **ДОХОД ПОДТВЕРЖДЕН И ЗАПИСАН В СВОДКУ**", parse_mode='Markdown')

        elif call.data.startswith("sub_side_"):
            p = call.data.split("_")
            income, r_pocket, r_drive, r_school, r_cushion, r_holidays, r_credit = map(float, p[2:])
            
            # Запись в статистику
            save_to_stats("подработка", income, r_pocket, r_drive, r_school, r_cushion, r_holidays, 0, 0, 0, r_credit)
            
            # Списание долга и пополнение Подушки
            b = load_balances()
            b["credit"] = max(0.0, b["credit"] - r_credit)
            b["cushion_accumulated"] += r_cushion
            save_balances(b["credit"], b["cushion_accumulated"])
            
            bot.answer_callback_query(call.id, "Запись обновлена!")
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                                  text=call.message.text + "\n\n✅ **ДОХОД ПОДТВЕРЖДЕН И ЗАПИСАН В СВОДКУ**", parse_mode='Markdown')
    except:
        bot.answer_callback_query(call.id, "❌ Ошибка подтверждения")

# =====================================================================
# МАСКИРОВКА ПОД ВЕБ-СЕРВИС ДЛЯ RENDER
# =====================================================================
app = Flask('')

@app.route('/')
def home():
    return "Финансовый движок полностью готов и активен!"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    bot.infinity_polling()
