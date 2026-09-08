import telebot
from telebot import types
import os
from datetime import datetime
from flask import Flask
import threading

# =====================================================================
# ТОКЕН БОТА И НАСТРОЙКИ
# =====================================================================
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
bot = telebot.TeleBot(TOKEN)

# Файлы для постоянного хранения данных на сервере
STAB_FILE = "stab_balance.txt"
HOLIDAYS_FILE = "holidays_balance.txt"
LOG_FILE = "history.txt"  # Лог-файл только для стабфонда и праздников

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

# Функция логирования только для Стабфонда и Праздников
def log_operation(envelope_name, operation_type, amount, new_balance):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sign = "+" if operation_type == "add" else "-"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] Конверт: {envelope_name} | Изменение: {sign}{amount:,.2f} ₽ | Новый баланс: {new_balance:,.2f} ₽\n")

# Точный календарь расходов по конкретным датам (из картинки)
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

# Расходы по месяцам
HOLIDAYS_CALENDAR = {
    1: 7000, 2: 0, 3: 12000, 4: 5000, 5: 2000, 6: 0,
    7: 1000, 8: 23000, 9: 3000, 10: 8000, 11: 0, 12: 10000
}

# Вспомогательная функция валидации чисел (Анти-дурак)
def validate_amount(text):
    try:
        val = float(text.strip().replace(',', '.'))
        if val <= 0:
            return None
        return val
    except ValueError:
        return None

# =====================================================================
# ГЛАВНОЕ МЕНЮ И СТАРТОВАЯ СПРАВКА
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
        "👋 **Привет! Я твой обновленный финансовый ассистент.**\n"
        "Контролирую Стабфонд, Праздники и защищаю бюджет от выгорания.\n\n"
        "🔧 **Скрытые команды управления (для корректировки балансов):**\n"
        "├ `/set XXXXX` — установить баланс Стабфонда (Пример: `/set 15000`)\n"
        "└ `/set_holidays XXXXX` — установить баланс Праздников (Пример: `/set_holidays 5000`)\n\n"
        "Используй интерактивные кнопки меню для распределения новых доходов 👇"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard(), parse_mode='Markdown')

# =====================================================================
# СКРЫТЫЕ КОМАНДЫ С VALIDATION (АНТИ-ДУРАК)
# =====================================================================
@bot.message_handler(commands=['set'])
def set_stab_balance(message):
    try:
        raw_val = message.text.split()[1]
        val = validate_amount(raw_val)
        if val is None: raise ValueError
        
        save_balance(STAB_FILE, val)
        log_operation("Стабфонд", "add", val, val)
        bot.reply_to(message, f"✅ Баланс Стабфонда успешно изменен на: **{val:,.2f} ₽**", parse_mode='Markdown')
    except:
        bot.reply_to(message, "❌ **Ошибка ввода!** Используйте формат: `/set 15000` (только положительные числа)", parse_mode='Markdown')

@bot.message_handler(commands=['set_holidays'])
def set_holidays_balance(message):
    try:
        raw_val = message.text.split()[1]
        val = validate_amount(raw_val)
        if val is None: raise ValueError
        
        save_balance(HOLIDAYS_FILE, val)
        log_operation("Праздники", "add", val, val)
        bot.reply_to(message, f"✅ Баланс Праздников изменен на: **{val:,.2f} ₽**", parse_mode='Markdown')
    except:
        bot.reply_to(message, "❌ **Ошибка ввода!** Используйте формат: `/set_holidays 5000` (только положительные числа)", parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "ℹ️ Мой Стабфонд")
def show_balances(message):
    stab = load_balance(STAB_FILE)
    hol = load_balance(HOLIDAYS_FILE)
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
        f"ℹ️ **ТЕКУЩИЕ НАКОПЛЕНИЯ В КОПИЛКАХ:**\n\n"
        f"🛡️ Конверт «Стабфонд»: **{stab:,.2f} ₽**\n"
        f"🎉 Конверт «Праздники» (всего): **{hol:,.2f} ₽**\n"
        f"📅 План расходов на текущий месяц: **{month_target:,.2f} ₽**\n"
    )
    if upcoming_alerts:
        msg += "\n🔔 **НАДВИГАЮЩИЕСЯ СОБЫТИЯ:**\n" + "\n".join(upcoming_alerts)
        
    bot.send_message(message.chat.id, msg, parse_mode='Markdown')
# =====================================================================
# ОБРАБОТЧИК ИНЛАЙН КНОПОК ПОПОЛНЕНИЯ
# =====================================================================
@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    try:
        current_stab = load_balance(STAB_FILE)
        current_holidays = load_balance(HOLIDAYS_FILE)
        
        # Кнопка подтверждения взноса (для Жирного режима и Подработок)
        if call.data.startswith("add_"):
            _, stab_add, hol_add = call.data.split("_")
            stab_add_f = float(stab_add)
            hol_add_f = float(hol_add)
            
            new_stab = current_stab + stab_add_f
            new_hol = current_holidays + hol_add_f
            
            save_balance(STAB_FILE, new_stab)
            save_balance(HOLIDAYS_FILE, new_hol)
            
            # Фиксация в текстовый файл (только эти 2 конверта)
            if stab_add_f > 0: 
                log_operation("Стабфонд", "add", stab_add_f, new_stab)
            if hol_add_f > 0: 
                log_operation("Праздники", "add", hol_add_f, new_hol)
            
            bot.answer_callback_query(call.id, "Успешно сохранено!")
            bot.edit_message_text(
                chat_id=call.message.chat.id, 
                message_id=call.message.message_id, 
                text=call.message.text + f"\n\n🟢 **ФИЗИЧЕСКИЙ ВЗНОС ПОДТВЕРЖДЕН:**\n└ Стабфонд обновлен: **{new_stab:,.2f} ₽**\n└ Праздники обновлены: **{new_hol:,.2f} ₽**", 
                parse_mode='Markdown'
            )

        # Кнопка подтверждения раскладки (когда дефицита нет)
        elif call.data.startswith("savebase_"):
            _, hol_add = call.data.split("_")
            hol_add_f = float(hol_add)
            
            new_hol = current_holidays + hol_add_f
            save_balance(HOLIDAYS_FILE, new_hol)
            
            if hol_add_f > 0: 
                log_operation("Праздники", "add", hol_add_f, new_hol)
            
            bot.answer_callback_query(call.id, "Сохранено!")
            bot.edit_message_text(
                chat_id=call.message.chat.id, 
                message_id=call.message.message_id, 
                text=call.message.text + f"\n\n🟢 **РАСКЛАДКА ПОДТВЕРЖДЕНА:**\n└ Копилка Праздников обновлена: **{new_hol:,.2f} ₽**", 
                parse_mode='Markdown'
            )
        # Кнопка покрытия дефицита из Стабфонда по сложной схеме приоритетов
        elif call.data.startswith("sub_"):
            _, total_sub, def_wife, def_pocket, def_hol = call.data.split("_")
            def_wife = float(def_wife)
            def_pocket = float(def_pocket)
            def_hol = float(def_hol)
            
            allocated_to_wife = 0.0
            allocated_to_pocket = 0.0
            allocated_to_holidays = 0.0
            
            temp_stab = current_stab
            
            # -----------------------------------------------------------------
            # ЭТАП 1: ДОЛЕВОЕ РАСПРЕДЕЛЕНИЕ МЕЖДУ ЖЕНЕЙ И КАРМАНОМ
            # -----------------------------------------------------------------
            combined_cash_deficit = def_wife + def_pocket
            
            if combined_cash_deficit > 0 and temp_stab > 0:
                if temp_stab >= combined_cash_deficit:
                    # Денег в Стабфонде хватает на оба базовых конверта
                    allocated_to_wife = def_wife
                    allocated_to_pocket = def_pocket
                    temp_stab -= combined_cash_deficit
                else:
                    # Денег не хватает. Делим баланс пропорционально дефициту:
                    # Жене уходит большая часть, в Карман — меньшая доля.
                    share_wife = def_wife / combined_cash_deficit if combined_cash_deficit > 0 else 0.7
                    share_pocket = 1.0 - share_wife
                    
                    allocated_to_wife = temp_stab * share_wife
                    allocated_to_pocket = temp_stab * share_pocket
                    temp_stab = 0.0
            
            # -----------------------------------------------------------------
            # ЭТАП 2: ДОВОДКА ПРАЗДНИКОВ (По остаточному принципу)
            # -----------------------------------------------------------------
            if temp_stab > 0 and def_hol > 0:
                if temp_stab >= def_hol:
                    allocated_to_holidays = def_hol
                    temp_stab -= def_hol
                else:
                    allocated_to_holidays = temp_stab
                    temp_stab = 0.0

            # -----------------------------------------------------------------
            # СОХРАНЕНИЕ РЕЗУЛЬТАТОВ И ОБНОВЛЕНИЕ БАЛАНСОВ
            # -----------------------------------------------------------------
            actual_withdrawn = current_stab - temp_stab
            new_hol = current_holidays + allocated_to_holidays
            
            save_balance(STAB_FILE, temp_stab)
            save_balance(HOLIDAYS_FILE, new_hol)
            
            # Запись транзакций в лог (только для двух наших конвертов)
            if actual_withdrawn > 0: 
                log_operation("Стабфонд", "sub", actual_withdrawn, temp_stab)
            if allocated_to_holidays > 0: 
                log_operation("Праздники", "add", allocated_to_holidays, new_hol)
            
            bot.answer_callback_query(call.id, "Дефицит распределен по долям!")
            
            result_msg = (
                f"\n\n⚠️ **СТАБФОНД РАСПРЕДЕЛЕН ПО ПРИОРИТЕТАМ:**\n"
                f"└ Списано из Стабфонда всего: **-{actual_withdrawn:,.2f} ₽**\n"
                f"└ Остаток в Стабфонде: **{temp_stab:,.2f} ₽**\n\n"
                f"📌 **Пропорциональное разделение долей:**\n"
                f"└ Направлено Жене (Большая доля): {allocated_to_wife:,.0f} / {def_wife:,.0f} ₽\n"
                f"└ Направлено в Карман (Меньшая доля): {allocated_to_pocket:,.0f} / {def_pocket:,.0f} ₽\n"
                f"└ Направлено в Праздники (Строго до лимита): {allocated_to_holidays:,.0f} / {def_hol:,.0f} ₽\n\n"
                f"🎉 Текущая копилка Праздников: **{new_hol:,.2f} ₽**"
            )
            bot.edit_message_text(
                chat_id=call.message.chat.id, 
                message_id=call.message.message_id, 
                text=call.message.text + result_msg, 
                parse_mode='Markdown'
            )
    except Exception as e:
        pass
# =====================================================================
# МАСКИРОВКА ПОД ВЕБ-СЕРВИС ДЛЯ RENDER (ФИНАЛЬНЫЙ БЛОК)
# =====================================================================
app = Flask('')

@app.route('/')
def home():
    return "Бот полностью настроен, защищен от ошибок и работает в облаке!"

def run_flask():
    # Автоматически подхватывает порт от хостинга (например, 8080)
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

if __name__ == '__main__':
    # Запуск Flask в отдельном потоке, чтобы он не мешал работе Telegram-бота
    threading.Thread(target=run_flask).start()
    
    # Бесконечный опрос серверов Telegram с автопереподключением при сбоях сети
    bot.infinity_polling()
