import telebot
from telebot import types
from datetime import datetime as dt
import threading

TOKEN = 'token'
bot = telebot.TeleBot(TOKEN)


class User:
    def __init__(self, user_id):
        self.user_id = user_id
        self.tasks = []
        self.reminders = []


users = {}


@bot.message_handler(commands=['start', 'help'])
def start(message):
    user_id = message.from_user.id
    if user_id not in users:
        users[user_id] = User(user_id)
    start_message = (
        "Привет! Я бот-планировщик задач.\n"
        "Я помогу вам организовать свои задачи:\n\n"
        "➕ /add - добавить новую задачу\n"
        "📋 /list - посмотреть список задач\n"
        "✅ /done - отметить выполненную задачу\n"
        "➕ /remind - добавить напоминание\n"
        "➖ /remind_remove - удалить напоминание\n"
        "📋 /remind_list - посмотреть список напоминаний \n\n"
        "Просто отправьте мне команду, чтобы начать!"
    )
    bot.send_message(user_id, start_message)


@bot.message_handler(commands=['add'])
def add_task(message):
    user_id = message.from_user.id
    if user_id not in users:
        users[user_id] = User(user_id)
    bot.send_message(user_id, "Введите описание задачи:")
    bot.register_next_step_handler(message, process_new_task)


def process_new_task(message):
    user_id = message.from_user.id
    if user_id not in users:
        users[user_id] = User(user_id)
    task_description = message.text
    users[user_id].tasks.append(task_description)
    bot.send_message(user_id, "Задача добавлена!")


@bot.message_handler(commands=['list'])
def list_tasks(message):
    user_id = message.from_user.id
    tasks = users[user_id].tasks
    if not tasks:
        bot.send_message(user_id, "Список задач пуст.", reply_markup=types.ReplyKeyboardRemove())
    else:
        task_list = "\n".join(f"{index + 1}. {task}" for index, task in enumerate(tasks))
        bot.send_message(user_id, "Список задач:\n" + task_list)


@bot.message_handler(commands=['done'])
def mark_done(message):
    user_id = message.from_user.id
    if user_id not in users:
        users[user_id] = User(user_id)
    tasks = users[user_id].tasks
    if not tasks:
        bot.send_message(user_id, "Список задач пуст.")
        return

    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    task_buttons = [types.KeyboardButton(task) for task in tasks]
    back_button = types.KeyboardButton("Назад")
    markup.add(*task_buttons, back_button)

    bot.send_message(user_id, "Выберите задачу для отметки выполнения:", reply_markup=markup)
    bot.register_next_step_handler(message, process_done_task)


def process_done_task(message):
    user_id = message.from_user.id
    task_done = message.text
    if task_done in users[user_id].tasks:
        users[user_id].tasks.remove(task_done)
        bot.send_message(user_id, f"Задача '{task_done}' отмечена как выполненная.")
    elif task_done == 'Назад':
        bot.send_message(user_id, "Возвращаюсь в главное меню...", reply_markup=types.ReplyKeyboardRemove())
        start(message)
    else:
        bot.send_message(user_id, "Выберите задачу из списка.")


@bot.message_handler(commands=['remind'])
def remind_task(message):
    user_id = message.from_user.id
    bot.send_message(user_id, "Введите дату и время напоминания\n в формате ДД.ММ.ГГ ЧЧ:ММ")
    bot.register_next_step_handler(message, process_remind_datetime)


def process_remind_datetime(message):
    user_id = message.from_user.id
    datetime_str = message.text
    try:
        remind_datetime = dt.strptime(datetime_str, '%d.%m.%y %H:%M')
        bot.send_message(user_id, "Введите текст напоминания:")
        bot.register_next_step_handler(message, lambda msg: process_remind_text(msg, remind_datetime))
    except ValueError:
        bot.send_message(user_id, "Неверный формат даты и времени. Пожалуйста, используйте ДД.ММ.ГГ ЧЧ:ММ.")


def process_remind_text(message, remind_datetime):
    user_id = message.from_user.id
    remind_text = message.text

    current_datetime = dt.now()
    time_difference = (remind_datetime - current_datetime).total_seconds()

    if time_difference > 0:
        if user_id in users:
            users[user_id].reminders.append((remind_datetime, remind_text))
        else:
            users[user_id] = User(user_id)
            users[user_id].reminders.append((remind_datetime, remind_text))

        threading.Timer(time_difference, send_reminder, args=(user_id, remind_text)).start()
        bot.send_message(user_id, f"Напоминание установлено на {remind_datetime.strftime('%d.%m.%y %H:%M')}.")
    else:
        bot.send_message(user_id, "Указанное время уже прошло. Невозможно установить напоминание.")


def send_reminder(user_id, remind_text):
    bot.send_message(user_id, f"Напоминание: {remind_text}")
    if user_id in users:
        user = users[user_id]
        user.reminders = [(remind_datetime, text) for remind_datetime, text in user.reminders if text != remind_text]


@bot.message_handler(commands=['remind_list'])
def remind_list(message):
    user_id = message.from_user.id
    if user_id in users:
        reminders = users[user_id].reminders
        if reminders:
            remind_list = "\n".join(
                f"{index + 1}. {remind[1]} - {remind[0].strftime('%d.%m.%y %H:%M')}" for index, remind in
                enumerate(reminders))
            bot.send_message(user_id, "Список напоминаний:\n" + remind_list)
        else:
            bot.send_message(user_id, "Список напоминаний пуст.")
    else:
        bot.send_message(user_id, "Список напоминаний пуст.")


@bot.message_handler(commands=['remind_remove'])
def remind_remove(message):
    user_id = message.from_user.id
    if user_id in users:
        reminders = users[user_id].reminders
        if reminders:
            markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
            reminder_buttons = [types.KeyboardButton(remind[1]) for remind in reminders]
            back_button = types.KeyboardButton("Назад")
            markup.add(*reminder_buttons, back_button)
            bot.send_message(user_id, "Выберите напоминание для удаления:", reply_markup=markup)
            bot.register_next_step_handler(message, process_remind_remove)
        else:
            bot.send_message(user_id, "Список напоминаний пуст.")
    else:
        bot.send_message(user_id, "Список напоминаний пуст.")


def process_remind_remove(message):
    user_id = message.from_user.id
    text = message.text

    if text == "Назад":
        bot.send_message(user_id, "Возвращаюсь в главное меню...", reply_markup=types.ReplyKeyboardRemove())
        start(message)
    else:
        if user_id in users:
            user = users[user_id]
            if any(remind[1] == text for remind in user.reminders):
                user.reminders = [(remind_datetime, remind_text) for remind_datetime, remind_text in user.reminders if
                                  remind_text != text]
                bot.send_message(user_id, f"Напоминание '{text}' удалено.")
                remind_list(message)
            else:
                bot.send_message(user_id, "Выберите напоминание из списка или нажмите 'Назад'.")
        else:
            bot.send_message(user_id, "Ошибка: пользователь не найден.")


if __name__ == '__main__':
    bot.polling(none_stop=True)
