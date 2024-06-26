from telebot.types import Message, CallbackQuery
from init.class_user import *
from init.keyboards import *
from init.messages import *
from init.db_funcs import *
from datetime import datetime
from decouple import config
from loguru import logger
import telebot


admin_list = [int(config('admin_1')), int(config('admin_2'))]
bot = telebot.TeleBot(config('football_bot'))
payment_link = config('payment_link')
users_dict = dict()


@bot.message_handler(content_types=['text'])
def start(message: Message) -> None:
    """ CALLING AND PROCESSING BASIC BOT COMMANDS """

    global users_dict

    user_chat_id = message.chat.id
    users_dict[user_chat_id] = create_user(message.chat, BotUser(message.chat))
    user = users_dict[user_chat_id]

    if message.text == '/start':
        bot.send_message(user_chat_id, start_message(message))
        bot.send_message(user_chat_id, function_list(user_chat_id))
    elif message.text == '/help':
        bot.send_message(user_chat_id, function_list(user_chat_id))
    elif message.text == '/training':
        training = get_future_training()
        if training:
            bot.send_message(user_chat_id, training_notice(training))
            bot.register_next_step_handler(message, add_to_training, training)
        else:
            bot.send_message(user_chat_id, no_training_info())
    elif message.text == "/training_info":
        training = get_future_training()
        if training:
            users_list = get_users_on_training(training[7])
            bot.send_message(user_chat_id, training_info(training, users_list))
        else:
            bot.send_message(user_chat_id, no_training_info())
    elif message.text == '/balance':
        user_info = get_info_about_user(user_chat_id)
        bot.send_message(user_chat_id, show_user_balance(user_info))
    elif message.text == '/pay':
        bot.send_message(user_chat_id, pay(), reply_markup=payment_link_keyboard(payment_link))
        bot.send_message(user_chat_id, enter_amount_msg())
        bot.register_next_step_handler(message, enter_amount)
    elif message.text == '/confirm_payments' and user.user_id in admin_list:
        new_payments = get_new_payments()
        if new_payments and len(new_payments) > 0:
            bot.send_message(user_chat_id, confirm_payments_msg())
            confirm_payment(user_chat_id, new_payments[0])
        else:
            bot.send_message(user_chat_id, no_confirm_payments_msg())
    elif message.text == '/confirm_training' and user.user_id in admin_list:
        training = get_future_training()

        if training:
            bot.send_message(user_chat_id, confirm_training_msg())
            users_list = get_users_on_training(training[7])
            bot.send_message(user_chat_id, text=confirm_training(training, users_list), reply_markup=training_confirm_keyboard())
        else:
            bot.send_message(user_chat_id, no_confirm_training_msg())
    elif message.text == '/change_training' and user.user_id in admin_list:
        training = get_future_training()

        if training:
            users_list = get_users_on_training(training[7])
            bot.send_message(user_chat_id, text=change_training_msg(training, users_list), reply_markup=change_training_keyboard())
        else:
            bot.send_message(user_chat_id, no_training_info())
    elif message.text == '/new_training' and user.user_id in admin_list:
        bot.send_message(user_chat_id, new_training_msg())
        bot.register_next_step_handler(message, new_training_date)
    elif message.text == '/active_subscription' and user.user_id in admin_list:
        bot.send_message(user_chat_id, input_username())
        bot.register_next_step_handler(message, change_subscription)
    elif message.text == '/users' and user.user_id in admin_list:
        send_users_list(user_chat_id)
    elif message.text == '/payments' and user.user_id in admin_list:
        send_payments_list(user_chat_id)
    else:
        bot.send_message(user_chat_id, function_list(user_chat_id))


@bot.callback_query_handler(func=lambda call: True)
def callback_worker(call: CallbackQuery) -> None:
    """ UPDATE PAYMENT STATUS FOR USER IN DB """

    user_id = call.message.chat.id
    user = users_dict[user_id]

    if ', ' in call.data:
        new_payment_status = call.data.split(', ')

        if new_payment_status[0] == 'confirmed':
            response, player_id = update_payment_in_db(new_payment_status)
        elif new_payment_status[0] == 'rejected':
            response, player_id = update_payment_in_db(new_payment_status)
        else:
            bot.send_message(user_id, 'Введен неверный вариант ответа...\nВыберите вариант из предложенных выше')
            response, player_id = 'error', None

        if response == 'confirmed':
            bot.send_message(user_id, payment_success_confirmed(player_id))
        elif response == 'rejected':
            bot.send_message(user_id, payment_success_rejected(player_id))
        else:
            bot.send_message(user_id, payment_success_error())

        bot.delete_message(user_id, call.message.message_id)
        new_payments = get_new_payments()
        if new_payments and len(new_payments) > 0:
            bot.send_message(user_id, confirm_payments_msg())
            confirm_payment(user_id, new_payments[0])
        else:
            bot.send_message(user_id, no_confirm_payments_msg())
    else:
        action = call.data

        if action == 'complete_training':
            training = get_future_training()
            response = complete_training(training)
            if response:
                bot.send_message(user_id, success_complete_training())
            else:
                bot.send_message(user_id, error_complete_training())
        elif action == 'cancel_training':
            training = get_future_training()
            response = cancel_training(training)
            if response:
                bot.send_message(user_id, success_cancel_training())
            else:
                bot.send_message(user_id, error_cancel_training())
        elif action == 'back_training':
            bot.send_message(user_id, back_from_confirm_training())
        elif 'active_subscription' in action:
            player_id = action.split('-')[1]
            if player_id.isdigit():
                player_id = int(player_id)
                response = active_subscription(player_id)
                if response:
                    bot.send_message(player_id, success_change_subscription())
                    bot.send_message(user_id, success_change_subscription())
                else:
                    bot.send_message(user_id, error_change_subscription())
        elif 'cancel_subscription' in action:
            player_id = action.split('-')[1]
            if player_id.isdigit():
                player_id = int(player_id)
                response = cancel_subscription(player_id)
                if response:
                    bot.send_message(player_id, success_change_subscription())
                    bot.send_message(user_id, success_change_subscription())
                else:
                    bot.send_message(user_id, error_change_subscription())
        elif action == 'time':
            bot.send_message(user_id, change_training_time_msg())
            bot.register_next_step_handler(call.message, change_training_time)
        elif action == 'date':
            bot.send_message(user_id, change_training_date_msg())
            bot.register_next_step_handler(call.message, change_training_date)
        elif action == 'prive_with_subscription':
            bot.send_message(user_id, change_training_sub_price_msg())
            bot.register_next_step_handler(call.message, change_training_sub_price)
        elif action == 'prive_without_subscription':
            bot.send_message(user_id, change_training_usual_price_msg())
            bot.register_next_step_handler(call.message, change_training_usual_price)
        bot.delete_message(user_id, call.message.message_id)


def new_training_date(message: Message):
    """ START TO CREATE NEW TRAINING FROM DATE """

    trainig_date = message.text
    user_id = message.chat.id
    user = users_dict[user_id]

    try:
        date = datetime.strptime(trainig_date, "%d.%m.%Y").date()
        new_trainig = Training(trainig_date)
        bot.send_message(user_id, new_training_time_msg())
        bot.register_next_step_handler(message, new_training_time, new_trainig)
    except Exception as error:
        # logger.error(f"Wrong input trainig date = {trainig_date} by {user}. Error: {error}")
        bot.send_message(user_id, 'Введена неверная дата тренировки...\nПопробуйте снова')
        # bot.register_next_step_handler(message, new_training_date)


def new_training_time(message: Message, new_trainig):
    """ CREATE NEW TRAINING FROM TIME """

    trainig_time = message.text
    user_id = message.chat.id
    user = users_dict[user_id]

    try:
        time = trainig_time.split('.')
        if len(time) == 2 and time[0].isdigit() and time[1].isdigit():
            new_trainig.time = trainig_time
            bot.send_message(user_id, new_training_price_subscription_msg())
            bot.register_next_step_handler(message, new_training_price_subscribe, new_trainig)
    except Exception as error:
        logger.error(f"Wrong input trainig time = {trainig_time} by {user}. Error: {error}")
        bot.send_message(user_id, 'Введено неверное время тренировки...\nПопробуйте снова')
        bot.register_next_step_handler(message, new_training_time)


def new_training_price_subscribe(message: Message, new_trainig):
    """ CREATE THE NEW TRAINING, ADD PRICE FOR SUBSCRIBE"""

    price = message.text
    user_id = message.chat.id
    user = users_dict[user_id]

    try:
        price_for_subscribe = float(price)
        new_trainig.price_for_subscribe = price_for_subscribe
        bot.send_message(user_id, new_training_price_msg())
        bot.register_next_step_handler(message, new_training_price, new_trainig)
    except Exception as error:
        logger.error(f"Wrong input trainig time = {trainig_price} by {user}. Error: {error}")
        bot.send_message(user_id, 'Введена неверная стоимость тренировки...\nПопробуйте снова')
        bot.register_next_step_handler(message, new_training_price_subscribe, new_trainig)


def new_training_price(message: Message, new_trainig):
    """ CREATE THE NEW TRAINING, ADD PRICE FOR USUAL """

    price = message.text
    user_id = message.chat.id
    user = users_dict[user_id]

    try:
        price_for_usual = float(price)
        new_trainig.price_for_usual = price_for_usual

        create_new_trainig(new_trainig)
        users = get_all_users_in_db()
        for user_id_in_db in users:
            if user_id_in_db == user_id:
                bot.send_message(user_id_in_db, new_training_was_created(new_trainig))
            else:
                bot.send_message(user_id_in_db, new_training_notice(new_trainig))
    except Exception as error:
        logger.error(f"Wrong input trainig time = {trainig_price} by {user}. Error: {error}")
        bot.send_message(user_id, 'Введена неверная стоимость тренировки...\nПопробуйте снова')
        bot.register_next_step_handler(message, new_training_price, new_trainig)


def add_to_training(message: Message, training):
    """ ADD USER TO TRAINING """

    user_voice = message.text
    user_id = message.chat.id
    user = users_dict[user_id]

    if user_voice == '+':
        add_user_success = add_user_to_training(user)
        if add_user_success == 'success':
            bot.send_message(user_id, add_to_training_success())
        elif add_user_success == 'added':
            bot.send_message(user_id, add_to_training_added())
        else:
            bot.send_message(user_id, add_to_training_error())
    elif user_voice == '-':
        bot.send_message(user_id, bad_voice_to_trainig())
    else:
        bot.send_message(user_id, 'Введен неверный вариант ответа...\nПопробуйте снова')
        # bot.register_next_step_handler(message, add_to_training, training)


def enter_amount(message: Message) -> None:
    """ CREATE A NEW PAYMENT FOR USER """

    pay_amount = message.text
    user_id = message.chat.id
    user = users_dict[user_id]
    today_date = str(datetime.now().date().strftime('%d.%m.%Y'))

    try:
        new_payment = Payment(user_id, user.username, today_date, float(pay_amount))
        create_payment(new_payment)
        bot.send_message(user_id, success_payment(new_payment))
    except Exception as error:
        logger.error(f"Wrong input pay amount = {pay_amount} by {user}. Error: {error}")
        bot.send_message(user_id, 'Введено неверная сумма перевода...\nПопробуйте снова')
        # bot.register_next_step_handler(message, enter_amount)


def confirm_payment(user_id, new_payment):
    """ START TO CONFIRM NEW PAYMENT """

    bot.send_message(
        user_id,
        text=payment_info_confirm(new_payment),
        reply_markup=payment_confirm_keyboard(new_payment)
    )


def send_users_list(user_id: int):
    """ SEND USERS LIST IN DOC """

    bot.send_message(user_id, users_list_doc())
    users_list = get_users_info()

    with open('users.txt', 'w+', encoding='utf-8') as file:
        for user_set in users_list:
            user = user_to_dict(user_set)
            user_str = user_to_str(user)
            file.write(user_str)
        file.close()

    bot.send_document(user_id, open('users.txt', 'rb'))


def send_payments_list(user_id: int):
    """ SEND PAYMENTS LIST IN DOC """

    bot.send_message(user_id, payments_list_doc())
    payments_list = get_payments_info()

    with open('payments.txt', 'w+', encoding='utf-8') as file:
        for payment_set in payments_list:
            payment = payment_to_dict(payment_set)
            payment_str = payment_to_str(payment)
            file.write(payment_str)
        file.close()

    bot.send_document(user_id, open('payments.txt', 'rb'))


def change_subscription(message: Message):
    """ CHANGE SUBSCRIPTION STATUS OF PLAYER"""

    user_text = message.text
    user_id = message.chat.id

    user, u_username, u_user_id = None, None, None

    if user_text.isdigit():
        u_user_id = int(user_text)
    else:
        u_username = f"{user_text}"

    if u_user_id:
        user = get_info_about_user(u_user_id)
    elif u_username:
        user = get_info_about_user_by_username(u_username)
    else:
        bot.send_message(user_id, error_change_subscription())

    if user:
        user_dict = user_to_dict(user)
        bot.send_message(
            user_id,
            text=action_subscription(user_dict),
            reply_markup=action_subscription_keyboard(user_dict['id'])
        )


def change_training_date(message: Message):
    """ CHANGE TRAINING DATE """

    trainig_date = message.text
    user_id = message.chat.id
    user = users_dict[user_id]

    try:
        training = get_future_training()
        new_date = datetime.strptime(trainig_date, "%d.%m.%Y").date()
        response = change_date(training, trainig_date)
        if response:
            bot.send_message(user_id, date_was_changed())
        else:
            bot.send_message(user_id, error_change_training())
    except Exception as error:
        bot.send_message(user_id, 'Введена неверная дата тренировки...\nПопробуйте снова')


def change_training_time(message: Message):
    """ CHANGE TRAINING TIME """

    trainig_time = message.text
    user_id = message.chat.id
    user = users_dict[user_id]

    try:
        time = trainig_time.split('.')
        if len(time) == 2 and time[0].isdigit() and time[1].isdigit():
            training = get_future_training()
            response = change_time(training, trainig_time)
            if response:
                bot.send_message(user_id, time_was_changed())
            else:
                bot.send_message(user_id, error_change_training())
        else:
            bot.send_message(user_id, 'Введена неверная дата тренировки...\nПопробуйте снова')
    except Exception as error:
        bot.send_message(user_id, 'Введена неверная дата тренировки...\nПопробуйте снова')


def change_training_sub_price(message: Message):
    """ CHANGE TRAINING PRICE WITH SUBSCRIPTION """

    sub_price = message.text
    user_id = message.chat.id
    user = users_dict[user_id]

    try:
        price_for_subscribe = float(sub_price)
        training = get_future_training()
        response = change_sub_price(training, price_for_subscribe)
        if response:
            bot.send_message(user_id, sub_price_was_changed())
        else:
            bot.send_message(user_id, error_change_training())
    except Exception as error:
        bot.send_message(user_id, 'Введена неверная сумма...\nПопробуйте снова')


def change_training_usual_price(message: Message):
    """ CHANGE TRAINING PRICE WITHOUT SUBSCRIPTION """

    price = message.text
    user_id = message.chat.id
    user = users_dict[user_id]

    try:
        usual_price = float(price)
        training = get_future_training()
        response = change_usual_price(training, usual_price)
        if response:
            bot.send_message(user_id, usual_price_was_changed())
        else:
            bot.send_message(user_id, error_change_training())
    except Exception as error:
        bot.send_message(user_id, 'Введена неверная сумма...\nПопробуйте снова')


if __name__ == '__main__':
    logger.add('logger.log', level='DEBUG', format='{time} | {level} | {message}', encoding='utf-8')
    bot.polling(none_stop=True, interval=0)
