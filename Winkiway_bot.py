import telebot
import sqlite3
from telebot import types
import datetime
import threading
import time

# Инициализация бота
API_TOKEN = '7725895379:AAEYqORZ45OThfNqbdtAXxv8kBQ1MYQ8jTw'
bot = telebot.TeleBot(API_TOKEN)

# Создание базы данных
conn = sqlite3.connect('tasks.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS tasks
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, teacher TEXT, subject TEXT, due_date TEXT, notification_time TEXT, reminder_days INTEGER)''')
conn.commit()


# Функция для отправки напоминаний
def send_reminders():
    while True:
        now = datetime.datetime.now()
        cursor.execute('SELECT chat_id, subject, notification_time FROM tasks')
        rows = cursor.fetchall()
        for row in rows:
            chat_id, subject, notification_time = row
            notification_datetime = datetime.datetime.strptime(notification_time, '%d.%m.%Y %H:%M')
            if now >= notification_datetime:
                bot.send_message(chat_id,
                                 f'Напоминание: У вас есть предмет {subject}, время для оповещения: {notification_datetime}.')

                # Удаляем задачу после отправки напоминания, чтобы не отправлять повторно
                cursor.execute('DELETE FROM tasks WHERE chat_id=? AND notification_time=?',
                               (chat_id, notification_time))
                conn.commit()
        time.sleep(60)  # Проверяем каждую минуту


# Команда /start
@bot.message_handler(commands=['start'])
def start_command(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button_start = types.KeyboardButton("Запустить бота")
    markup.add(button_start)
    bot.send_message(message.chat.id, "Добро пожаловать! Нажмите 'Запустить бота'", reply_markup=markup)


# Обработка нажатия кнопки "Запустить бота"
@bot.message_handler(func=lambda message: message.text == "Запустить бота")
def run_bot(message):
    bot.send_message(message.chat.id,
                     "Ты студент 1 курса? Ты увидел нашу грандиозную рекламу и перешел по ссылке или QR коду? О да, сынок! Ты попал по адресу! "
                     "Мы готовы предоставить тебе спектр услуг, и все твои экзамены будут в кармане (в твоей зачетке).")

    # Кнопки для дальнейшего взаимодействия
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button_help = types.KeyboardButton("Помощь")
    button_view = types.KeyboardButton("Посмотреть долги")
    button_delete = types.KeyboardButton("Удалить долг")
    markup.add(button_help, button_view, button_delete)
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)


# Обработка ввода информации о предмете
@bot.message_handler(
    func=lambda message: message.text not in ["Запустить бота", "Помощь", "Посмотреть долги", "Удалить долг"])
def add_task(message):
    try:
        # Попробуем разделить строку на части
        parts = message.text.split(", ")
        if len(parts) != 5:
            raise ValueError(
                "Неверное количество параметров. Убедитесь, что вводите в формате: Преподаватель, Предмет, Дата дедлайна (ДД.ММ.ГГГГ), Время оповещения (ЧЧ:ММ), Дней до напоминания.")

        teacher = parts[0]
        subject = parts[1]
        due_date_str = parts[2].strip()  # Дата дедлайна
        notification_time_str = parts[3].strip()  # Время оповещения
        reminder_days = int(parts[4].strip())  # Дней до напоминания

        # Сохраняем дату дедлайна и рассчитываем время уведомления
        due_date = datetime.datetime.strptime(due_date_str, '%d.%m.%Y')
        notification_time = datetime.datetime.strptime(notification_time_str, '%H:%M')

        # Вычисляем время для оповещения
        notify_datetime = due_date - datetime.timedelta(days=reminder_days)
        notify_datetime = notify_datetime.replace(hour=notification_time.hour, minute=notification_time.minute)

        # Сохранение задачи в базу данных
        cursor.execute(
            'INSERT INTO tasks (chat_id, teacher, subject, due_date, notification_time, reminder_days) VALUES (?, ?, ?, ?, ?, ?)',
            (
            message.chat.id, teacher, subject, due_date_str, notify_datetime.strftime('%d.%m.%Y %H:%M'), reminder_days))
        conn.commit()

        bot.send_message(message.chat.id, "Задача добавлена!")
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка: {e}. Убедитесь, что информация введена в правильном формате:\n"
                                          "Пример: Иванов, Математика, 26.10.2024, 14:40, 2")


# Команда /help
@bot.message_handler(func=lambda message: message.text == "Помощь")
def help_command(message):
    bot.send_message(message.chat.id,
                                      "Введите информацию в формате:\n"
                                      "Преподаватель, Предмет, Дата дедлайна (ДД.ММ.ГГГГ), Время оповещения (ЧЧ:ММ), Дней до напоминания.")


## Команда /view
@bot.message_handler(func=lambda message: message.text == "Посмотреть долги")
def view_command(message):
    cursor.execute('SELECT subject FROM tasks WHERE chat_id=?', (message.chat.id,))
    rows = cursor.fetchall()
    if rows:
        response = "Твои долги. Давай поднажми!\n" + "\n".join([row[0] for row in rows])
    else:
        response = "Ты красавчик, на твоем счету нет ни одного долга!"
    bot.send_message(message.chat.id, response)



# Команда /delete
@bot.message_handler(func=lambda message: message.text == "Удалить долг")
def delete_command(message):
    cursor.execute('SELECT id, subject FROM tasks WHERE chat_id=?', (message.chat.id,))
    rows = cursor.fetchall()
    if rows:
        markup = types.InlineKeyboardMarkup()
        for row in rows:
            button = types.InlineKeyboardButton(text=row[1], callback_data=f'delete_{row[0]}')
            markup.add(button)
        bot.send_message(message.chat.id, "Выбери, что удалить:", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "Нет долгов для удаления.")


# Обработка нажатия на кнопку удаления
@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_'))
def confirm_delete(call):
    task_id = int(call.data.split('_')[1])
    cursor.execute('DELETE FROM tasks WHERE id=? AND chat_id=?', (task_id, call.message.chat.id))
    if cursor.rowcount > 0:
        conn.commit()
        bot.send_message(call.message.chat.id, "Долг удален!, ты справился с этим, дружище! Ты большой молодец, продолжай дерзать гранит науки и диплом будет у тебя на полке!")
    else:
        bot.send_message(call.message.chat.id, "Ошибка: такой долг не найден.")


# Запуск потока для напоминаний
reminder_thread = threading.Thread(target=send_reminders)
reminder_thread.start()

# Запуск бота
bot.polling(none_stop=True)
