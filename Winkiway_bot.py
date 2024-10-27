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
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, teacher TEXT, subject TEXT, due_date TEXT, notification_time TEXT)''')
conn.commit()


# Функция для отправки напоминаний
def send_reminders():
    while True:
        now = datetime.datetime.now()
        cursor.execute('SELECT id, chat_id, subject, due_date, notification_time FROM tasks')
        rows = cursor.fetchall()
        for row in rows:
            task_id, chat_id, subject, due_date_str, notification_time = row
            due_date = datetime.datetime.strptime(due_date_str, '%d.%m.%Y')
            notification_datetime = datetime.datetime.strptime(notification_time, '%d.%m.%Y %H:%M')

            # Отправляем напоминание в указанное пользователем время
            if now >= notification_datetime:
                bot.send_message(chat_id,
                                 f'Напоминание: Дружище, пора поднажать у тебя долг по {subject}, время для оповещения: {notification_datetime}.')

                # Удаляем задачу после отправки напоминания
                cursor.execute('DELETE FROM tasks WHERE id=?', (task_id,))
                conn.commit()

            # Отправляем напоминание за день до дедлайна, если задача не удалена
            elif now >= due_date - datetime.timedelta(days=1) and now < due_date:
                bot.send_message(chat_id,
                                 f'Напоминание: Дружище, у тебя должок горит, давай поднажми {subject}.')

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
        parts = message.text.split(", ")
        if len(parts) != 4:
            raise ValueError(
                "Неверное количество параметров. Убедитесь, что вводите в формате: Преподаватель, Предмет, Дата дедлайна (ДД.ММ.ГГГГ), Время оповещения (ДД.ММ.ГГГГ ЧЧ:ММ).")

        teacher = parts[0]
        subject = parts[1]
        due_date_str = parts[2].strip()  # Дата дедлайна
        notification_time_str = parts[3].strip()  # Время оповещения

        due_date = datetime.datetime.strptime(due_date_str, '%d.%m.%Y')
        notification_datetime = datetime.datetime.strptime(notification_time_str, '%d.%m.%Y %H:%M')

        cursor.execute(
            'INSERT INTO tasks (chat_id, teacher, subject, due_date, notification_time) VALUES (?, ?, ?, ?, ?)',
            (message.chat.id, teacher, subject, due_date_str, notification_datetime.strftime('%d.%m.%Y %H:%M')))
        conn.commit()

        bot.send_message(message.chat.id, "Задача добавлена!")
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка: {e}. Убедитесь, что информация введена в правильном формате:\n"
                                          "Пример: Иванов, Математика, 26.10.2024, 25.10.2024 14:40")


# Команда /help
@bot.message_handler(func=lambda message: message.text == "Помощь")
def help_command(message):
    bot.send_message(message.chat.id,
                     "Введите информацию в формате:\n"
                     "Преподаватель, Предмет, Дата дедлайна (ДД.ММ.ГГГГ), Время оповещения (ДД.ММ.ГГГГ ЧЧ:ММ).")


# Команда /view
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
        bot.send_message(call.message.chat.id, "Долг удален! Ты справился с этим, дружище! Продолжай дерзать!")
    else:
        bot.send_message(call.message.chat.id, "Ошибка: такой долг не найден.")


# Запуск потока для напоминаний
reminder_thread = threading.Thread(target=send_reminders)
reminder_thread.start()

# Отключаем webhook
bot.remove_webhook()

# Запуск бота
bot.polling(none_stop=True)
