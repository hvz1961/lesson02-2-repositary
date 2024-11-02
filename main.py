from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

checklist = [
    "Заполнение ингредиентами",
    "Сделать фото",
    "Добавление расходников (стаканы/крышки/размешиватели)",
    "Сделать фото",
    "Слив из емкости жидких отходов (если есть)",
    "Промывка поддона для жидких отходов",
    "Промывка поддона для жмыха",
    "Выброс пакета с мусором",
    "Промывка миксеров",
    "Промывка УЗК",
    "Проверить уровень воды, добавить при необходимости",
    "Сделать фото",
    "Запустить режим автоматической очистки",
    "Влажная уборка стойки",
    "Замена сиропов",
    "Сделать фото",
    "Внесение сведений в Телеметрон"
]

equipment_list = {
    "Панфилова,12": "Адрес: ул. Панфилова, д. 12",
    "Салон Каприз": "Адрес: ул. Панфилова, д. 19",
    "Институт НИИМ": "Адрес: ул. Парадная, д. 9"
}

current_step = {}
completed_tasks = {}

CHANNEL_ID = '  '

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    keyboard = [
        [KeyboardButton("Старт")],
        [KeyboardButton("Список оборудования")],
        [KeyboardButton("Назад")],
        [KeyboardButton("Меню")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(f"Привет, {user.first_name}! Выберите действие:", reply_markup=reply_markup)


async def equipment_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[KeyboardButton(equipment) for equipment in equipment_list.keys()]]
    keyboard.append([KeyboardButton("Назад")])
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Выберите оборудование:", reply_markup=reply_markup)


async def selected_equipment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    selected = update.message.text
    if selected in equipment_list:
        user_id = update.message.from_user.id
        current_step[user_id] = 0
        completed_tasks[user_id] = {
            "equipment": selected,
            "steps": []
        }
        await update.message.reply_text(
            f"Вы выбрали {selected}.\nАдрес: {equipment_list[selected]}\nНачинаем обслуживание!")
        await next_step(update, context)


async def next_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    step = current_step.get(user_id, 0)

    if step < len(checklist):
        await process_checklist_step(update, context, step)
    else:
        await update.message.reply_text("Техническое обслуживание завершено!")

        # Кнопка "Отправить" для формирования и отправки отчета
        keyboard = [[KeyboardButton("Отправить")]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Нажмите «Отправить» для формирования и отправки отчета.",
                                        reply_markup=reply_markup)


async def process_checklist_step(update: Update, context: ContextTypes.DEFAULT_TYPE, step: int):
    user_id = update.message.from_user.id
    current_step[user_id] = step

    keyboard = [
        [KeyboardButton("Да"), KeyboardButton("Нет")],
        [KeyboardButton("Добавить комментарий")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(f"Шаг {step + 1}: {checklist[step]}\nВыберите действие или добавьте комментарий.",
                                    reply_markup=reply_markup)


async def handle_step_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    # Проверка наличия пользователя в current_step
    if user_id not in current_step:
        await update.message.reply_text("Пожалуйста, выберите оборудование и начните процесс обслуживания с начала.")
        return

    step = current_step[user_id]

    response = update.message.text
    if response in ["Да", "Нет"]:
        completed_tasks[user_id]["steps"].append({
            "step": step,
            "task": checklist[step],
            "response": response,
            "comment": ""
        })
        current_step[user_id] += 1
        await next_step(update, context)
    elif response == "Добавить комментарий":
        await update.message.reply_text("Введите комментарий:")
    else:
        completed_tasks[user_id]["steps"][-1]["comment"] = response
        current_step[user_id] += 1
        await next_step(update, context)


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    step = current_step.get(user_id, 0) - 1

    # Проверяем, что step находится в допустимых пределах
    if step < 0 or step >= len(checklist):
        await update.message.reply_text("Вы не можете отправить фото на этом этапе. Пожалуйста, следуйте шагам.")
        return

    photo_file = await update.message.photo[-1].get_file()  # Исправлено на await для корректного получения файла
    completed_tasks[user_id]["steps"].append({
        "step": step,
        "task": checklist[step],
        "photo": photo_file,
        "response": "Фото",
        "comment": ""
    })
    await update.message.reply_text("Фото сохранено. Можете продолжить выполнение шагов.")


async def send_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    # Проверяем, есть ли данные для отправки отчета
    if user_id not in completed_tasks:
        await update.message.reply_text("Нет данных для отчета. Пожалуйста, пройдите все шаги.")
        return

    report_text = f"Отчет по обслуживанию оборудования: {completed_tasks[user_id]['equipment']}\n\n"

    # Формируем текст отчета
    for task in completed_tasks[user_id]["steps"]:
        report_text += f"Шаг {task['step'] + 1}: {task['task']}\nОтвет: {task['response']}\nКомментарий: {task['comment']}\n\n"

    try:
        # Отправляем текст отчета в канал
        await context.bot.send_message(chat_id=CHANNEL_ID, text=report_text)

        # Отправляем фотографии, если они есть
        for task in completed_tasks[user_id]["steps"]:
            if "photo" in task:
                await context.bot.send_photo(chat_id=CHANNEL_ID, photo=task["photo"].file_id)

        await update.message.reply_text("Отчет успешно отправлен!")

        # Сброс состояния после отправки отчета
        current_step[user_id] = 0
        completed_tasks[user_id] = {}

        # Возвращаем пользователя в главное меню
        keyboard = [
            [KeyboardButton("Старт")],
            [KeyboardButton("Список оборудования")],
            [KeyboardButton("Назад")],
            [KeyboardButton("Меню")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Выберите следующее действие:", reply_markup=reply_markup)

    except Exception as e:
        print(f"Ошибка при отправке отчета: {e}")
        await update.message.reply_text("Произошла ошибка при отправке отчета. Пожалуйста, попробуйте еще раз.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Используй /start для начала и кнопки для выполнения операций.")


def main():
    TOKEN = '    '
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.Regex("^(Список оборудования)$"), equipment_selection))
    app.add_handler(MessageHandler(filters.Regex("^(Старт)$"), next_step))
    app.add_handler(MessageHandler(filters.Regex("^(Назад)$"), equipment_selection))
    app.add_handler(MessageHandler(filters.Regex("|".join(equipment_list.keys())), selected_equipment))
    app.add_handler(MessageHandler(filters.Regex("^(Да|Нет|Добавить комментарий)$"), handle_step_response))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.Regex("^(Да|Нет|Добавить комментарий)$"), handle_step_response))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.Regex("^(Отправить)$"), send_report))

    app.run_polling()


if __name__ == '__main__':
    main()
