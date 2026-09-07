import telebot
from telebot import types
import os
from datetime import datetime
from flask import Flask
import threading

# =====================================================================
# ТОКЕН БОТА
# =====================================================================
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
bot = telebot.TeleBot(TOKEN)

# Файлы для постоянного хранения балансов на сервере
STAB_FILE = "stab_balance.txt"
HOLIDAYS_FILE = "holidays_balance.txt"

def load_balance(filename):
    if not os.path.exists(filename):
        return 0.0
    try:
        with open(filename, "r") as f:
            return float(f.read().strip())
    except:
        return 0.0

def save_balance(filename, value):
    with open(filename, "w") as f:
        f.write(f"{value:.2f}")

# Динамический календарь расходов на праздники по месяцам в году
HOLIDAYS_CALENDAR = {
    1: 7000, 2: 0, 3: 12000, 4: 5000, 5: 2000, 6: 0,
    7: 1000, 8: 23000, 9: 3000, 10: 8000, 11: 0, 12: 10000
}

# =====================================================================
# ГЛАВНОЕ МЕНЮ (КНОПКИ)
# =====================================================================
def get_main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_cash = types.KeyboardButton("💵 Основной доход")
    btn_side = types.KeyboardButton("🚀 Подработка")
    btn_status = types.KeyboardButton("ℹ️ Мой Стабфонд")
    keyboard.add(btn_cash, btn_side)
    keyboard.add(btn_status)
    return keyboard

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "👋 Привет! Я твой обновленный финансовый ассистент конвертов.\n"
        "Управляю Стабфондом, балансом Праздников и защищаю Карман от выгорания.\n\n"
        "Используй кнопки внизу для ввода доходов."
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard(), parse_mode='Markdown')

# =====================================================================
# СКРЫТЫЕ КОМАНДЫ КОРРЕКТИРОВКИ БАЛАНСОВ
# =====================================================================
@bot.message_handler(commands=['set'])
def set_stab_balance(message):
    try:
        val = float(message.text.split()[1])
        save_balance(STAB_FILE, val)
        bot.reply_to(message, f"✅ Баланс Стабфонда успешно изменен на: **{val:,.2f} ₽**", parse_mode='Markdown')
    except:
        bot.reply_to(message, "❌ Формат: `/set 15000`", parse_mode='Markdown')

@bot.message_handler(commands=['set_holidays'])
def set_holidays_balance(message):
    try:
        val = float(message.text.split()[1])
        save_balance(HOLIDAYS_FILE, val)
        bot.reply_to(message, f"✅ Накопленный баланс Праздников изменен на: **{val:,.2f} ₽**", parse_mode='Markdown')
    except:
        bot.reply_to(message, "❌ Формат: `/set_holidays 5000`", parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "ℹ️ Мой Стабфонд")
def show_balances(message):
    stab = load_balance(STAB_FILE)
    hol = load_balance(HOLIDAYS_FILE)
    current_month = datetime.now().month
    month_target = HOLIDAYS_CALENDAR.get(current_month, 0)
    
    msg = (
        f"ℹ️ **ТЕКУЩИЕ НАКОПЛЕНИЯ В КОПИЛКАХ:**\n\n"
        f"🛡️badge Конверт «Стабфонд»: **{stab:,.2f} ₽**\n"
        f"🎉 Конверт «Праздники» (накоплено всего): **{hol:,.2f} ₽**\n"
        f"📅 План расходов на текущий месяц: **{month_target:,.2f} ₽**"
    )
    bot.send_message(message.chat.id, msg, parse_mode='Markdown')

# =====================================================================
# ЛОГИКА ОБРАБОТКИ ВВОДА
# =====================================================================
@bot.message_handler(func=lambda m: m.text == "💵 Основной доход")
def ask_cash(message):
    msg = bot.send_message(message.chat.id, "💵 Отлично! Введите общую сумму наличных от продаж:")
    bot.register_next_step_handler(msg, process_cash)

def process_cash(message):
    try:
        income = float(message.text.strip())
        wife_cash = max(50000.0, income * 0.6)
        c7 = max(0.0, income - wife_cash)
        
        current_month = datetime.now().month
        holiday_target_this_month = HOLIDAYS_CALENDAR.get(current_month, 0)
        current_holidays_stock = load_balance(HOLIDAYS_FILE)
        
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

            stab_avail = load_balance(STAB_FILE)
            deficit_wife = max(0.0, 50000.0 - (income * 0.6)) if income * 0.6 < 50000.0 else 0.0
            deficit_pocket = max(0.0, 10000.0 - pocket) if c7 >= 14750 else 0.0
            
            needed_holiday_injection = max(0.0, holiday_target_this_month - current_holidays_stock - holidays)
            if holiday_target_this_month == 0:
                needed_holiday_injection = 0.0
                
            total_deficit = deficit_wife + deficit_pocket + needed_holiday_injection
            
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
                f"🪦 Конверт «Памятники»: **{monuments:,.0f} ₽**\n"
                f"🛡️ Конверт «Стабфонд»: **0 ₽**\n\n"
            )
            
            if total_deficit > 0:
                report += (
                    f"🚑 **Потребность в Стабфонде:**\n"
                    f"└ Нехватка жене: {deficit_wife:,.0f} ₽\n"
                    f"└ Доводка Кармана: {deficit_pocket:,.0f} ₽\n"
                    f"└ Нехватка Праздников на месяц: {needed_holiday_injection:,.0f} ₽\n"
                    f"└ **Итого требуется изъять: {total_deficit:,.0f} ₽**\n\n"
                )
                if stab_avail >= total_deficit:
                    markup = types.InlineKeyboardMarkup()
                    btn = types.InlineKeyboardButton(f"⚠️ Покрыть дефицит из Стабфонда", callback_data=f"sub_{total_deficit}_{deficit_wife}_{deficit_pocket}_{needed_holiday_injection}")
                    markup.add(btn)
                    bot.send_message(message.chat.id, report + f"🟢 В Стабфонде достаточно средств ({stab_avail:,.0f} ₽). Нажми кнопку для физического покрытия дефицита.", reply_markup=markup, parse_mode='Markdown')
                else:
                    report += f"❌ В Стабфонде недостаточно средств (Доступно: {stab_avail:,.0f} ₽). Расчет оставлен в исходном процентном виде."
                    bot.send_message(message.chat.id, report, parse_mode='Markdown')
            else:
                markup = types.InlineKeyboardMarkup()
                btn = types.InlineKeyboardButton("Физически разложено по конвертам ✅", callback_data=f"savebase_{holidays}")
                markup.add(btn)
                bot.send_message(message.chat.id, report, reply_markup=markup, parse_mode='Markdown')

        else:
            mode_name = "🟩 Жирный режим"
            wife_cash = income * 0.60
            c7 = income * 0.40
            
            holidays = 5750.0
            health = 2000.0
            auto = 5000.0
            monuments = 2000.0
            
            stabfond = (c7 - 14750.0) * 0.15
            free_remainder = (c7 - 14750.0) * 0.85
            
            masya_school = free_remainder * 0.10
            personal_pool = free_remainder * 0.90
            
            pocket = personal_pool * 0.60
            cushion = personal_pool * 0.20
            drive = 3000.0 + (personal_pool * 0.20)
            
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
                f"🛍 Конверт «Карман»: **{pocket:,.0f} ₽**\n"
                f"🏎 Конверт «Драйв»: **{drive:,.0f} ₽**\n"
                f"🎉 Фонд праздников: **{holidays:,.0f} ₽**\n"
                f"🩺 Конверт «Здоровье»: **{health:,.0f} ₽**\n"
                f"🚗 Автофонд: **{auto:,.0f} ₽**\n"
                f"🎒 Мася школа: **{masya_school:,.0f} ₽**\n"
                f"🏦 Конверт «Подушка»: **{cushion:,.0f} ₽**\n"
                f"🪦 Конверт «Памятники»: **{monuments:,.0f} ₽**\n"
                f"🛡️ Конверт «Стабфонд» (начислено): **{stabfond:,.0f} ₽**"
            )
            markup = types.InlineKeyboardMarkup()
            btn = types.InlineKeyboardButton("Внесено в Стабфонд ✅", callback_data=f"add_{stabfond}_{holidays}")
            markup.add(btn)
            bot.send_message(message.chat.id, report, reply_markup=markup, parse_mode='Markdown')
            
    except Exception as e:
        bot.send_message(message.chat.id, "❌ Произошла ошибка при расчете.")

health -= rem_deficit * (health / sum_funds)
wife_cash = 55000.0
report = (
f"📊 РАСЧЕТ ОСНОВНОГО ДОХОДА ({income:,.0f} ₽)\n"
f"⚙️ Режим твоей доли: {mode_name}\n\n"
f"💵 Наличные (От продаж):\n"
f"└ 👩 Жене наличными (60%): {wife_cash:,.0f} ₽\n"
f"└ 🧔 Твоя чистая доля (40%): {c7:,.0f} ₽\n\n"
f"🗂 Распределение по твоим конвертам:"
f"🛍 Конверт «Карман»: {pocket:,.0f} ₽\n"
f"🏎 Конверт «Драйв»: {drive:,.0f} ₽\n"
f"🎉 Фонд праздников: {holidays:,.0f} ₽\n"
f"🩺 Конверт «Здоровье»: {health:,.0f} ₽\n"
f"🚗 Автофонд: {auto:,.0f} ₽\n"
f"🎒 Мася школа: {masya_school:,.0f} ₽\n"
f"🏦 Конверт «Подушка»: {cushion:,.0f} ₽\n"
f"🪦 Конверт «Памятники»: {monuments:,.0f} ₽\n"
f"🛡️ Конверт «Стабфонд» (начислено): {stabfond:,.0f} ₽"
)
markup = types.InlineKeyboardMarkup()
btn = types.InlineKeyboardButton("Внесено в Стабфонд ✅", callback_data=f"add_{stabfond}_{holidays}")
markup.add(btn)
bot.send_message(message.chat.id, report, reply_markup=markup, parse_mode='Markdown')
            
except Exception as e:
        bot.send_message(message.chat.id, "❌ Произошла ошибка при расчете.")


=====================================================================

БЛОК ПОДРАБОТОК

=====================================================================

@bot.message_handler(func=lambda m: m.text == "🚀 Подработка")
def ask_side(message):
msg = bot.send_message(message.chat.id, "🚀 Отлично! Введите сумму случайной подработки:")
bot.register_next_step_handler(msg, process_side)

def process_side(message):
try:
e2 = float(message.text.strip())

if e2 <= 2000:
level_name = "🌱 Микро (до 2к)"
p_pocket, p_drive, p_credit, p_school, p_holidays, p_cushion, p_stab = 0.50, 0.20, 0.15, 0.05, 0.02, 0.02, 0.01
elif e2 <= 5000:
level_name = "📈 Стандарт (2к - 5к)"
p_pocket, p_drive, p_credit, p_school, p_holidays, p_cushion, p_stab = 0.45, 0.15, 0.20,
0.10, 0.03, 0.04, 0.03
elif e2 <= 8000:
level_name = "🚀 Профи (5к - 8к)"
p_pocket, p_drive, p_credit, p_school, p_holidays, p_cushion, p_stab = 0.45, 0.15, 0.20,
0.12, 0.03, 0.03, 0.02
else:level_name = "🔥 Турбо-Досрочка (Выше 8к)"
p_pocket, p_drive, p_credit, p_school, p_holidays, p_cushion, p_stab = 0.50, 0.15, 0.15,
0.12, 0.03, 0.03, 0.02

pocket = e2 * p_pocket
drive = e2 * p_drive
credit = e2 * p_credit
school = e2 * p_school
holidays = e2 * p_holidays
cushion = e2 * p_cushion
stab = e2 * p_stab

report = (
f"🚀 РАСЧЕТ ПОДРАБОТКИ ({e2:,.0f} ₽)\n"
f"⚡ Уровень дохода: {level_name}\n\n"
f"📉 ДОСРОЧКА КРЕДИТА: {credit:,.0f} ₽ 🔥 (сразу гаси долг!)\n\n"
f"🗂 В твои конверты:\n"
f"🛍 Конверт «Карман»: {pocket:,.0f} ₽\n"
f"🏎 Конверт «Драйв»: {drive:,.0f} ₽\n"
f"🎒 Конверт «Мася школа»: {school:,.0f} ₽\n"
f"🎉 Фонд праздников: {holidays:,.0f} ₽\n"
f"🏦 Конверт «Подушка»: {cushion:,.0f} ₽\n"
f"🛡️ Конверт «Стабфонд» (начислено): {stab:,.0f} ₽"
)

markup = types.InlineKeyboardMarkup()
btn = types.InlineKeyboardButton("Внесено в Стабфонд ✅", 
callback_data=f"add_{stab}_{holidays}")
markup.add(btn)
bot.send_message(message.chat.id, report, reply_markup=markup, 
parse_mode='Markdown')

except ValueError:
bot.send_message(message.chat.id, "❌ Пожалуйста, введи только число.")

=====================================================================

ОБРАБОТЧИК НАЖАТИЙ НА ИНЛАЙН-КНОПКИ

=====================================================================

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
try:
current_stab = load_balance(STAB_FILE)
current_holidays = load_balance(HOLIDAYS_FILE)

if call.data.startswith("add_"):
, stab_add, hol_add = call.data.split("")
new_stab = current_stab + float(stab_add)
new_hol = current_holidays + float(hol_add)

save_balance(STAB_FILE, new_stab)
save_balance(HOLIDAYS_FILE, new_hol)

bot.answer_callback_query(call.id, "Успешно сохранено!")
bot.edit_message_text(chat_id=call.message.chat.id, 
message_id=call.message.message_id,
text=call.message.text + f"\n\n🟢 ФИЗИЧЕСКИЙ ВЗНОС ПОДТВЕРЖДЕН:\n└ 
Стабфонд обновлен: {new_stab:,.2f} ₽\n└ Праздники обновлены: {new_hol:,.2f} ₽", parse_mode='Markdown')

elif call.data.startswith("savebase_"):
, hol_add = call.data.split("")
new_hol = current_holidays + float(hol_add)
save_balance(HOLIDAYS_FILE, new_hol)

bot.answer_callback_query(call.id, "Сохранено!")
bot.edit_message_text(chat_id=call.message.chat.id,
message_id=call.message.message_id,
text=call.message.text + f"\n\n🟢 РАСКЛАДКА ПОДТВЕРЖДЕНА:\n└ Копилка 
Праздников обновлена: {new_hol:,.2f} ₽", parse_mode='Markdown')

elif call.data.startswith("sub_"):
, total_sub, def_wife, def_pocket, def_hol = call.data.split("")
total_sub = float(total_sub)

if current_stab >= total_sub:
new_stab = current_stab - total_sub
new_hol = current_holidays + float(def_hol)

save_balance(STAB_FILE, new_stab)
save_balance(HOLIDAYS_FILE, new_hol)

bot.answer_callback_query(call.id, "Дефицит покрыт!")
bot.edit_message_text(chat_id=call.message.chat.id,
message_id=call.message.message_id,
text=call.message.text + f"\n\n⚠️ ДЕФИЦИТ ПОКРЫТ ИЗ СТАБФОНДА:\n└ Списано из 
Стабфонда: -{total_sub:,.2f} ₽\n└ Остаток в Стабфонде: {new_stab:,.2f} ₽\n└ 
Добавлено жене и в Карман до нормы.\n└ Праздничный буфер обновлен: 
{new_hol:,.2f} ₽", parse_mode='Markdown')
else:
bot.answer_callback_query(call.id, "❌ Недостаточно средств в Стабфонде!",
show_alert=True)except:
pass

=====================================================================

МАСКИРОВКА ПОД ВЕБ-СЕРВИС ДЛЯ RENDER

=====================================================================

app = Flask('')
@app.route('/')
def home():
return "Бот работает!"
def run_flask():
app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
if name == 'main':
threading.Thread(target=run_flask).start()
bot.infinity_polling()
