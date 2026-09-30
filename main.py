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

HOLIDAYS_CALENDAR = {
    1: 7000, 2: 0, 3: 12000, 4: 5000, 5: 2000, 6: 0,
    7: 1000, 8: 23000, 9: 3000, 10: 8000, 11: 0, 12: 10000
}

# =====================================================================
# ФУНКЦИИ СИСТЕМЫ ХРАНЕНИЯ ДАННЫХ
# =====================================================================
def load_balances():
    """Загружает текущие остатки Кредита и Подушки"""
    default_balances = {"credit": 125423.45, "cushion_accumulated": 0.0}
    if not os.path.exists(BALANCES_FILE):
        return default_balances
    try:
        with open(BALANCES_FILE, "r", encoding="utf-8") as f:
            data = f.read().strip().split("|")
            if len(data) < 2:
                return default_balances
            return {
                "credit": max(0.0, float(data)),
                "cushion_accumulated": max(0.0, float(data))
            }
    except:
        return default_balances

def save_balances(credit, cushion):
    """Сохраняет текущие остатки Кредита и Подушки"""
    with open(BALANCES_FILE, "w", encoding="utf-8") as f:
        f.write(f"{credit:.2f}|{cushion:.2f}")

def save_to_stats(income_type, total, pocket, drive, school, cushion, holidays=0, health=0, auto=0, monuments=0, credit=0, clothes=0):
    """Записывает подтвержденный доход в файл статистики"""
    month_key = datetime.now().strftime("%Y-%m")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    row = (
        f"{month_key}|{timestamp}|{income_type}|{total:.2f}|{pocket:.2f}|{drive:.2f}|"
        f"{school:.2f}|{cushion:.2f}|{holidays:.2f}|{health:.2f}|{auto:.2f}|{monuments:.2f}|{credit:.2f}|{clothes:.2f}\n"
    )
    with open(STATS_FILE, "a", encoding="utf-8") as f:
        f.write(row)
# =====================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ И ИНТЕРФЕЙС БОТА
# =====================================================================
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
        "👋 **Financial Engine v5.9 [TAX_4_PERCENT] активирован.**\n"
        "Налог на Одежду повышен до 4%. Устранены расхождения Кармана и Драйва.\n"
        "Внедрены лимиты: Праздники (5.5к), Авто (5к), Памятники (2к везде).\n\n"
        "🔧 **Команны управления целями (балансами):**\n"
        "├ `/set_credit XXXXX` — изменить остаток долга по Кредиту\n"
        "│  (Пример: `/set_credit 125423.45`)\n"
        "└ `/set_cushion XXXXX` — изменить баланс Подушки безопасности\n"
        "   (Пример: `/set_cushion 15000`)\n\n"
        "Используй кнопки меню для расчетов 👇"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard(), parse_mode='Markdown')

# =====================================================================
# КОМАНДЫ РУЧНОГО ИЗМЕНЕНИЯ БАЛАНСОВ
# =====================================================================
@bot.message_handler(commands=['set_credit'])
def set_credit_balance(message):
    try:
        parts = message.text.split()
        if len(parts) < 2: raise ValueError
        val = float(parts[1].strip().replace(',', '.'))
        if val < 0: raise ValueError
        
        b = load_balances()
        b["credit"] = val
        save_balances(b["credit"], b["cushion_accumulated"])
        bot.reply_to(message, f"✅ Остаток долга по Кредиту изменен на: **{val:,.2f} ₽**", parse_mode='Markdown')
    except:
        bot.reply_to(message, "❌ **Ошибка ручной корректировки!**\nФормат: `/set_credit 125423.45`", parse_mode='Markdown')

@bot.message_handler(commands=['set_cushion'])
def set_cushion_balance(message):
    try:
        parts = message.text.split()
        if len(parts) < 2: raise ValueError
        val = float(parts[1].strip().replace(',', '.'))
        if val < 0: raise ValueError
        
        b = load_balances()
        b["cushion_accumulated"] = val
        save_balances(b["credit"], b["cushion_accumulated"])
        bot.reply_to(message, f"✅ Баланс Подушки безопасности изменен на: **{val:,.2f} ₽**", parse_mode='Markdown')
    except:
        bot.reply_to(message, "❌ **Ошибка ручной корректировки!**\nФормат: `/set_cushion 15000`", parse_mode='Markdown')
# =====================================================================
# НАГЛЯДНЫЙ ДВУХМЕСЯЧНЫЙ ЕЖЕМЕСЯЧНЫЙ ОТЧЕТ
# =====================================================================
@bot.message_handler(func=lambda m: m.text == "⚙️ Мои Балансы и Цели")
def show_balances_screen(message):
    b = load_balances()
    msg = (
        f"⚙️ **ТЕКУЩЕЕ СОСТОЯНИЕ ЦЕЛЕЙ:**\n\n"
        f"📉 Остаток по Кредиту: **{b['credit']:,.2f} ₽**\n"
        f"🏦 Накоплено в Подушку: **{b['cushion_accumulated']:,.2f} ₽** / 100,000 ₽\n"
    )
    bot.send_message(message.chat.id, msg, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "📊 Ежемесячный отчет")
def show_monthly_report(message):
    now = datetime.now()
    current_month = now.strftime("%Y-%m")
    
    if now.month == 1:
        prev_month = f"{now.year - 1}-12"
    else:
        prev_month = f"{now.year}-{now.month - 1:02d}"
    
    total_main, total_side, total_prev = 0.0, 0.0, 0.0
    r_pocket, r_drive, r_school, r_cushion, r_holidays, r_health, r_auto, r_monuments, r_credit, r_clothes = [0.0]*10
    
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("|")
                if len(parts) < 14: continue
                
                if parts[0] == prev_month:
                    total_prev += float(parts[3])
                
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
                    r_clothes += float(parts[13])
                        
    total_earned = total_main + total_side
    
    msg = (
        f"📊 **ФИНАНСОВЫЙ ОТЧЕТ**\n"
        f"📅 Период: `{current_month}`\n"
        f"═══════════════════════════\n\n"
        f"📈 **ДВИЖЕНИЕ КАПИТАЛА:**\n"
        f"├ 💰 Всего вошло: **{total_earned:,.2f} ₽**\n"
        f"├ 💵 Основной доход: {total_main:,.2f} ₽\n"
        f"└ 🚀 Из подработок: {total_side:,.2f} ₽\n\n"
        f"🛡️ **БЕЗОПАСНОСТЬ И БУДУЩЕЕ:**\n"
    )
    
    sec_safe = ""
    if r_credit > 0: sec_safe += f"├ 📉 Досрочка кредита: {r_credit:,.0f} ₽\n"
    if r_cushion > 0: sec_safe += f"├ 🏦 Подушка безопасности: {r_cushion:,.0f} ₽\n"
    if r_school > 0: sec_safe += f"├ 🎒 Мася школа: {r_school:,.0f} ₽\n"
    if r_auto > 0: sec_safe += f"├ 🚗 Автофонд: {r_auto:,.0f} ₽\n"
    if r_health > 0: sec_safe += f"├ 🩺 Здоровье: {r_health:,.0f} ₽\n"
    if r_monuments > 0: sec_safe += f"└ 🪦 Памятники: {r_monuments:,.0f} ₽\n"
    
    if sec_safe: msg += sec_safe + "\n"
    else: msg += "└ Конверты этой группы пусты\n\n"
    
    msg += f"🔥 **СВОБОДА И ЖИЗНЬ:**\n"
    sec_life = ""
    if r_pocket > 0: sec_life += f"├ 🛍 Чистый Карман: {r_pocket:,.0f} ₽\n"
    if r_drive > 0: sec_life += f"├ 🏎 Конверт Драйв: {r_drive:,.0f} ₽\n"
    if r_clothes > 0: sec_life += f"├ 👔 Одежда (Шмотки): {r_clothes:,.0f} ₽\n"
    if r_holidays > 0: sec_life += f"└ 🎉 Фонд праздников: {r_holidays:,.0f} ₽\n"
    
    if sec_life: msg += sec_life + "\n"
    else: msg += "└ Конверты этой группы пусты\n\n"
    
    msg += (
        f"═══════════════════════════\n"
        f"📅 **ДЛЯ СРАВНЕНИЯ:**\n"
        f"└ ⏪ Заработано в `{prev_month}`: **{total_prev:,.2f} ₽**"
    )
    
    bot.send_message(message.chat.id, msg, parse_mode='Markdown')

# =====================================================================
# НАЧАЛО БЛОКА ОБРАБОТКИ ВВОДА ОСНОВНОГО ДОХОДА
# =====================================================================
@bot.message_handler(func=lambda m: m.text == "💵 Основной доход")
def ask_cash(message):
    msg = bot.send_message(message.chat.id, "💵 Отлично! Введите общую сумму наличных от продаж:")
    bot.register_next_step_handler(msg, process_cash)
def calculate_cash_distribution(income, is_cushion_full):
    """Функция расчета основного дохода с налогом 4% и жесткими лимитами"""
    c7 = income * 0.40
    pocket, drive, holidays, health, auto, cushion, monuments, masya_school = [0.0]*8
    
    if income <= 37500:
        mode_name = "🟥 Уровень 1: Выживание (до 37.5к)"
        p_pocket, p_drive, p_school, p_holidays, p_health, p_auto, p_cushion, p_monuments = 0.68, 0.00, 0.12, 0.00, 0.08, 0.07, 0.05, 0.00
        if is_cushion_full:
            p_pocket += p_cushion
            p_cushion = 0.0
        pocket, drive, masya_school, holidays, health, auto, cushion, monuments = c7*p_pocket, c7*p_drive, c7*p_school, c7*p_holidays, c7*p_health, c7*p_auto, c7*p_cushion, c7*p_monuments

    elif income <= 75000:
        mode_name = "🟧 Уровень 2: Стабилизация (от 37.5к до 75к)"
        p_pocket, p_drive, p_school, p_holidays, p_health, p_auto, p_cushion, p_monuments = 0.40, 0.15, 0.12, 0.15, 0.08, 0.12, 0.10, 0.00
        if is_cushion_full:
            p_pocket += p_cushion
            p_cushion = 0.0
        pocket, drive, masya_school, cushion, holidays, health, auto, monuments = c7*p_pocket, c7*p_drive, c7*p_school, c7*p_cushion, c7*p_holidays, c7*p_health, c7*p_auto, c7*p_monuments

    elif income <= 125000:
        mode_name = "🟨 Уровень 3: Развитие (от 75к до 125к)"
        p_pocket, p_drive, p_school, p_holidays, p_health, p_auto, p_cushion, p_monuments = 0.50, 0.14, 0.12, 0.10, 0.06, 0.10, 0.07, 0.05
        if is_cushion_full:
            p_pocket += p_cushion
            p_cushion = 0.0
        pocket, drive, masya_school, cushion, holidays, health, auto, monuments = c7*p_pocket, c7*p_drive, c7*p_school, c7*p_cushion, c7*p_holidays, c7*p_health, c7*p_auto, c7*p_monuments
        
        if monuments > 2000.0:
            pocket += (monuments - 2000.0)
            monuments = 2000.0

    else:
        mode_name = "♾ Уровень 4: Жирный режим (выше 125к)"
        p_pocket, p_drive, p_school, p_holidays, p_health, p_auto, p_cushion, p_monuments = 0.38, 0.15, 0.12, 0.10, 0.05, 0.10, 0.10, 0.05
        if is_cushion_full:
            p_pocket += p_cushion
            p_cushion = 0.0
        pocket, drive, masya_school, cushion, holidays, health, auto, monuments = c7*p_pocket, c7*p_drive, c7*p_school, c7*p_cushion, c7*p_holidays, c7*p_health, c7*p_auto, c7*p_monuments
        
        if holidays > 5500.0:
            pocket += (holidays - 5500.0)
            holidays = 5500.0
        if auto > 5000.0:
            pocket += (auto - 5000.0)
            auto = 5000.0
        if monuments > 2000.0:
            pocket += (monuments - 2000.0)
            monuments = 2000.0

    # ПОВЫШЕННЫЙ СКВОЗНОЙ НАЛОГ 4% (со всех, КРОМЕ Мася школа)
    clothes = (pocket * 0.04) + (drive * 0.04) + (holidays * 0.04) + (health * 0.04) + (auto * 0.04) + (cushion * 0.04) + (monuments * 0.04)
    pocket, drive, holidays, health, auto, cushion, monuments = pocket*0.96, drive*0.96, holidays*0.96, health*0.96, auto*0.96, cushion*0.96, monuments*0.96

    r_drive = math.floor(drive / 10) * 10
    r_holidays = math.floor(holidays / 10) * 10
    r_health = math.floor(health / 10) * 10
    r_auto = math.floor(auto / 10) * 10
    r_monuments = math.floor(monuments / 10) * 10
    r_masya_school = math.floor(masya_school / 10) * 10
    r_clothes = math.floor(clothes / 10) * 10
    r_cushion = math.floor(cushion / 10) * 10
    
    allocated_except_pocket = r_drive + r_holidays + r_health + r_auto + r_monuments + r_masya_school + r_clothes + r_cushion
    r_pocket = c7 - allocated_except_pocket

    return mode_name, r_pocket, r_drive, r_masya_school, r_cushion, r_holidays, r_health, r_auto, r_monuments, r_clothes

def process_cash(message):
    try:
        income = validate_amount(message.text)
        if income is None:
            msg = bot.send_message(message.chat.id, "❌ **Ошибка ввода!** Введите корректное положительное число:")
            bot.register_next_step_handler(msg, process_cash)
            return

        b = load_balances()
        is_cushion_full = b["cushion_accumulated"] >= 100000.0
        wife_cash, c7 = income * 0.60, income * 0.40
        
        mode_name, r_pocket, r_drive, r_masya_school, r_cushion, r_holidays, r_health, r_auto, r_monuments, r_clothes = calculate_cash_distribution(income, is_cushion_full)

        report = (
            f"📊 **РАСЧЕТ ОСНОВНОГО ДОХОДА ({income:,.0f} ₽)**\n"
            f"⚙️ Режим твоей доли: `{mode_name}`\n\n"
            f"💵 **Наличные (От продаж):**\n"
            f"└ 👩 Жене наличными (60%): **{wife_cash:,.0f} ₽**\n"
            f"└ 🧔 Твоя чистая доля (40%): **{c7:,.0f} ₽**\n\n"
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
        if r_cushion > 0: report += f"🏦 Конверт «Подушка»: **{r_cushion:,.0f} ₽**"
        
        markup = types.InlineKeyboardMarkup()
        cb_data = f"sm_{income}"
        btn = types.InlineKeyboardButton("📝 Подтвердить и записать доход", callback_data=cb_data)
        markup.add(btn)
        bot.send_message(message.chat.id, report, reply_markup=markup, parse_mode='Markdown')
            
    except Exception as e:
        bot.send_message(message.chat.id, "❌ Произошла непредвиденная ошибка расчетов основного дохода.\n(Code: `ERR_CASH_CALC`)")
# =====================================================================
# БЛОК ПОДРАБОТОК И ЗАПУСК СЕРВИСА (ЧАСТЬ А)
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

        pocket, drive, credit, school, holidays, cushion, auto = [0.0] * 7
        
        if e2 > 15000:
            level_name = "🔥 5. ТУРБО Сверхдоход (Выше 15к)"
            pocket = 6000.0
            leftover = e2 - 6000.0
            drive, school, holidays, auto = leftover * 0.10, leftover * 0.10, leftover * 0.05, leftover * 0.10
            rem_pool = leftover * 0.65
            
            if is_credit_done and is_cushion_full: pocket += rem_pool
            elif is_credit_done: pocket += rem_pool * 0.70; cushion = rem_pool * 0.30
            elif is_cushion_full: pocket += rem_pool * 0.70; credit = rem_pool * 0.30
            else: credit, cushion = rem_pool * 0.30, rem_pool * 0.30; pocket += rem_pool * 0.40
        else:
            if e2 <= 2000: p_pocket, p_drive, p_credit, p_school, p_holidays, p_cushion, p_auto = 0.54, 0.10, 0.06, 0.10, 0.00, 0.06, 0.08
            elif e2 <= 5000: p_pocket, p_drive, p_credit, p_school, p_holidays, p_cushion, p_auto = 0.46, 0.15, 0.08, 0.10, 0.05, 0.08, 0.08
            elif e2 <= 10000: p_pocket, p_drive, p_credit, p_school, p_holidays, p_cushion, p_auto = 0.42, 0.15, 0.15, 0.10, 0.07, 0.03, 0.08
            else: p_pocket, p_drive, p_credit, p_school, p_holidays, p_cushion, p_auto = 0.40, 0.15, 0.15, 0.12, 0.06, 0.04, 0.08

            if is_credit_done: p_cushion += p_credit; p_credit = 0.0
            if is_cushion_full: p_pocket += p_cushion; p_cushion = 0.0
            pocket, drive, credit, school, holidays, cushion, auto = e2*p_pocket, e2*p_drive, e2*p_credit, e2*p_school, e2*p_holidays, e2*p_cushion, e2*p_auto

        clothes = (pocket * 0.04) + (drive * 0.04) + (holidays * 0.04) + (cushion * 0.04) + (credit * 0.04) + (auto * 0.04)
        pocket, drive, holidays, cushion, credit, auto = pocket * 0.96, drive * 0.96, holidays * 0.96, cushion * 0.96, credit * 0.96, auto * 0.96

        r_pocket = math.floor(pocket / 10) * 10
        r_drive = math.floor(drive / 10) * 10
        r_school = math.floor(school / 10) * 10
        r_holidays = math.floor(holidays / 10) * 10
        r_clothes = math.floor(clothes / 10) * 10
        r_cushion = math.floor(cushion / 10) * 10
        r_auto = math.floor(auto / 10) * 10

        overflow_to_pocket = 0.0
        if 0 < r_drive < 100: overflow_to_pocket += r_drive; r_drive = 0.0
        if 0 < r_holidays < 100: overflow_to_pocket += r_holidays; r_holidays = 0.0
        if 0 < r_clothes < 100: overflow_to_pocket += r_clothes; r_clothes = 0.0
        if 0 < r_cushion < 100: overflow_to_pocket += r_cushion; r_cushion = 0.0
        if 0 < r_auto < 100: overflow_to_pocket += r_auto; r_auto = 0.0
        r_pocket += overflow_to_pocket

        if 0 < r_school < 100:
            needed_diff = 100.0 - r_school
            if r_pocket >= needed_diff: r_pocket -= needed_diff; r_school = 100.0
            else: r_pocket += r_school; r_school = 0.0
        elif r_school == 0.0 and e2 >= 300.0:
            if r_pocket >= 100.0: r_pocket -= 100.0; r_school = 100.0

        if credit > 0:
            allocated_except_credit = r_pocket + r_drive + r_school + r_holidays + r_cushion + r_clothes + r_auto
            r_credit = e2 - allocated_except_credit
            if 0 < r_credit < 100: r_pocket += r_credit; r_credit = 0.0
            elif r_credit < 0: r_pocket += r_credit; r_credit = 0.0
        else:
            r_credit = 0.0
            allocated_except_cushion = r_pocket + r_drive + r_school + r_holidays + r_clothes + r_auto
            r_cushion = e2 - allocated_except_cushion
            if 0 < r_cushion < 100: r_pocket += r_cushion; r_cushion = 0.0

        report = (
            f"🚀 **РАСЧЕТ ПОДРАБОТКИ ({e2:,.0f} ₽)**\n"
            f"⚡ Уровень дохода: `{level_name}`\n\n"
        )
        if r_credit > 0: report += f"📉 **Досрочка кредита:** **{r_credit:,.0f} ₽** 🔥\n\n"

        report += "🗂 **В твои конверты:**\n"
        if r_pocket > 0: report += f"🛍 Конверт «Карман»: **{r_pocket:,.0f} ₽**\n"
        if r_drive > 0: report += f"🏎 Конверт «Драйв»: **{r_drive:,.0f} ₽**\n"
        if r_clothes > 0: report += f"👔 Конверт «Гардероб» (Шмотки): **{r_clothes:,.0f} ₽**\n"
        if r_school > 0: report += f"🎒 Конверт «Мася школа»: **{r_school:,.0f} ₽**\n"
        if r_cushion > 0: report += f"🏦 Конверт «Подушка»: **{r_cushion:,.0f} ₽**\n"
        if r_holidays > 0: report += f"🎉 Фонд праздников: **{r_holidays:,.0f} ₽**\n"
        if r_auto > 0: report += f"🚗 Автофонд: **{r_auto:,.0f} ₽**\n"
        
        markup = types.InlineKeyboardMarkup()
        cb_data = f"ss_{e2}"
        markup.add(types.InlineKeyboardButton("📝 Подтвердить и записать доход", callback_data=cb_data))
        bot.send_message(message.chat.id, report, reply_markup=markup, parse_mode='Markdown')
        
    except Exception as e:
        bot.send_message(message.chat.id, "❌ Произошла ошибка обработки подработки.\n(Code: `ERR_SIDE_CALC`)")
def calculate_side_distribution(e2, is_credit_done, is_cushion_full):
    """Вспомогательная функция для динамического пересчета подработок в момент клика с налогом 4%"""
    pocket, drive, credit, school, holidays, cushion, auto = [0.0] * 7
    if e2 > 15000:
        pocket = 6000.0
        leftover = e2 - 6000.0
        drive, school, holidays, auto = leftover*0.10, leftover*0.10, leftover*0.05, leftover*0.10
        rem_pool = leftover * 0.65
        if is_credit_done and is_cushion_full: pocket += rem_pool
        elif is_credit_done: pocket += rem_pool * 0.70; cushion = rem_pool * 0.30
        elif is_cushion_full: pocket += rem_pool * 0.70; credit = rem_pool * 0.30
        else: credit, cushion = rem_pool*0.30, rem_pool*0.30; pocket += rem_pool*0.40
    else:
        if e2 <= 2000: p_pocket, p_drive, p_credit, p_school, p_holidays, p_cushion, p_auto = 0.54, 0.10, 0.06, 0.10, 0.00, 0.06, 0.08
        elif e2 <= 5000: p_pocket, p_drive, p_credit, p_school, p_holidays, p_cushion, p_auto = 0.46, 0.15, 0.08, 0.10, 0.05, 0.08, 0.08
        elif e2 <= 10000: p_pocket, p_drive, p_credit, p_school, p_holidays, p_cushion, p_auto = 0.42, 0.15, 0.15, 0.10, 0.07, 0.03, 0.08
        else: p_pocket, p_drive, p_credit, p_school, p_holidays, p_cushion, p_auto = 0.40, 0.15, 0.15, 0.12, 0.06, 0.04, 0.08

        if is_credit_done: p_cushion += p_credit; p_credit = 0.0
        if is_cushion_full: p_pocket += p_cushion; p_cushion = 0.0
        pocket, drive, credit, school, holidays, cushion, auto = e2*p_pocket, e2*p_drive, e2*p_credit, e2*p_school, e2*p_holidays, e2*p_cushion, e2*p_auto

    clothes = (pocket * 0.04) + (drive * 0.04) + (holidays * 0.04) + (cushion * 0.04) + (credit * 0.04) + (auto * 0.04)
    pocket, drive, holidays, cushion, credit, auto = pocket*0.96, drive*0.96, holidays*0.96, cushion*0.96, credit*0.96, auto*0.96
    r_pocket, r_drive, r_school, r_holidays, r_clothes, r_cushion, r_auto = math.floor(pocket/10)*10, math.floor(drive/10)*10, math.floor(school/10)*10, math.floor(holidays/10)*10, math.floor(clothes/10)*10, math.floor(cushion/10)*10, math.floor(auto/10)*10

    overflow_to_pocket = 0.0
    if 0 < r_drive < 100: overflow_to_pocket += r_drive; r_drive = 0.0
    if 0 < r_holidays < 100: overflow_to_pocket += r_holidays; r_holidays = 0.0
    if 0 < r_clothes < 100: overflow_to_pocket += r_clothes; r_clothes = 0.0
    if 0 < r_cushion < 100: overflow_to_pocket += r_cushion; r_cushion = 0.0
    if 0 < r_auto < 100: overflow_to_pocket += r_auto; r_auto = 0.0
    r_pocket += overflow_to_pocket

    if 0 < r_school < 100:
        needed_diff = 100.0 - r_school
        if r_pocket >= needed_diff: r_pocket -= needed_diff; r_school = 100.0
        else: r_pocket += r_school; r_school = 0.0
    elif r_school == 0.0 and e2 >= 300.0:
        if r_pocket >= 100.0: r_pocket -= 100.0; r_school = 100.0

    if credit > 0:
        allocated_except_credit = r_pocket + r_drive + r_school + r_holidays + r_cushion + r_clothes + r_auto
        r_credit = e2 - allocated_except_credit
        if 0 < r_credit < 100: r_pocket += r_credit; r_credit = 0.0
        elif r_credit < 0: r_pocket += r_credit; r_credit = 0.0
    else:
        r_credit = 0.0
        allocated_except_cushion = r_pocket + r_drive + r_school + r_holidays + r_clothes + r_auto
        r_cushion = e2 - allocated_except_cushion
        if 0 < r_cushion < 100: r_pocket += r_cushion; r_cushion = 0.0

    return r_pocket, r_drive, r_school, r_cushion, r_holidays, r_credit, r_clothes, r_auto
# =====================================================================
# ОБРАБОТЧИК CALLBACK И СЕТЕВОЙ ЗАПУСК ДВИЖКА (ФИНАЛЬНЫЙ БЛОК)
# =====================================================================
@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    try:
        # ОБРАБОТКА СЖАТОГО ПАКЕТА ОСНОВНОГО ДОХОДА
        if call.data.startswith("sm_"):
            # ИСПРАВЛЕН КРАШ: Берем второй элемент списка после разделения строки [1]
            income = float(call.data.split("_")[1])
            b = load_balances()
            is_cushion_full = b["cushion_accumulated"] >= 100000.0
            
            # Динамический пересчет в момент клика по сохраненной формуле [1]
            _, r_pocket, r_drive, r_school, r_cushion, r_holidays, r_health, r_auto, r_monuments, r_clothes = calculate_cash_distribution(income, is_cushion_full)
            
            save_to_stats("основной", income, r_pocket, r_drive, r_school, r_cushion, r_holidays, r_health, r_auto, r_monuments, 0.0, r_clothes)
            
            b["cushion_accumulated"] += r_cushion
            save_balances(b["credit"], b["cushion_accumulated"])
            
            bot.answer_callback_query(call.id, "Доход успешно зафиксирован!")
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                                  text=call.message.text + "\n\n✅ **ДОХОД ПОДТВЕРЖДЕН И ЗАПИСАН В СВОДКУ**", parse_mode='Markdown')

        # ОБРАБОТКА СЖАТОГО ПАКЕТА ПОДРАБОТОК
        elif call.data.startswith("ss_"):
            # ИСПРАВЛЕН КРАШ: Берем второй элемент списка после разделения строки [1]
            e2 = float(call.data.split("_")[1])
            b = load_balances()
            is_credit_done = b["credit"] <= 0.0
            is_cushion_full = b["cushion_accumulated"] >= 100000.0
            
            # Динамический пересчет подработок в момент клика [1]
            r_pocket, r_drive, r_school, r_cushion, r_holidays, r_credit, r_clothes, r_auto = calculate_side_distribution(e2, is_credit_done, is_cushion_full)
            
            save_to_stats("подработка", e2, r_pocket, r_drive, r_school, r_cushion, r_holidays, 0, r_auto, 0, r_credit, r_clothes)
            
            b["credit"] = max(0.0, b["credit"] - r_credit)
            b["cushion_accumulated"] += r_cushion
            save_balances(b["credit"], b["cushion_accumulated"])
            
            bot.answer_callback_query(call.id, "Запись обновлена!")
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                                  text=call.message.text + "\n\n✅ **ДОХОД ПОДТВЕРЖДЕН И ЗАПИСАН В СВОДКУ**", parse_mode='Markdown')
    except Exception as e:
        bot.answer_callback_query(call.id, "❌ Ошибка подтверждения (Code: `ERR_CB_FALLBACK`)")

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
