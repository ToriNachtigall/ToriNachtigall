import aiosqlite
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram import F
logging.basicConfig(level=logging.INFO)
API_TOKEN = 'you token'
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
DB_NAME = 'quiz_bot.db'

file = open('example.txt','r',encoding='utf-8')
onstring = file.read().split("\n")[:-1]
quiz_data = []
d = {}
for item in onstring:
    key = item.split(", ")[0]
    value = item.split(", ")[1:]
    if key == "correct_option":
        item = map(int, item)
        int_value = value[0]
        d[key] = int_value
        quiz_data.append(d.copy())
    elif key == "question":
        d[key] = value[0]
    else:
        d[key] = value
quiz_data.append(d.copy())
print(*quiz_data, sep='\n')


def generate_options_keyboard(answer_options, right_answer):
    builder = InlineKeyboardBuilder()
    
    for option in answer_options:
        otv="wrong_answer" + '_' + option
        builder.add(types.InlineKeyboardButton(
            text=option,
            callback_data="right_answer" if option == right_answer else otv))

    builder.adjust(1)
    return builder.as_markup()


@dp.callback_query(F.data == "right_answer")
async def right_answer(callback: types.CallbackQuery):

    await callback.bot.edit_message_reply_markup(
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        reply_markup=None
    )
    current_question_index = await get_quiz_index(callback.from_user.id)
    correct_qiz_option = await get_quiz_ansver(callback.from_user.id)
    correct_option = quiz_data[current_question_index]['correct_option']
    await callback.message.answer(f"Верно! ваш ответ: {quiz_data[current_question_index]['options'][int(correct_option)]}")
    # Обновление номера текущего вопроса в базе данных
    correct_qiz_option += 1
    current_question_index += 1
    await update_quiz_index(callback.from_user.id, current_question_index, correct_qiz_option)


    if current_question_index < len(quiz_data):
        await get_question(callback.message, callback.from_user.id)
    else:
        await callback.message.answer("Это был последний вопрос. Квиз завершен!")
        await callback.message.answer(f"вы ответили правильно {correct_qiz_option}")


@dp.callback_query(F.data.startswith("wrong_answer_"))
async def wrong_answer(callback: types.CallbackQuery):
    await callback.bot.edit_message_reply_markup(
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        reply_markup=None
    )
    action = callback.data.split("_")[2]
    current_question_index = await get_quiz_index(callback.from_user.id)
    correct_qiz_option = await get_quiz_ansver(callback.from_user.id)
    await callback.message.answer(f"Неправильно. ваш ответ: {action[0]}")
    current_question_index += 1
    await update_quiz_index(callback.from_user.id, current_question_index,correct_qiz_option)


    if current_question_index < len(quiz_data):
        await get_question(callback.message, callback.from_user.id)
    else:
        await callback.message.answer("Это был последний вопрос. Квиз завершен!")
        await callback.message.answer(f"вы ответили правильно {correct_qiz_option}")


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="Начать игру"))
    builder.add(types.KeyboardButton(text="Результаты"))
    await message.answer("Добро пожаловать в квиз!", reply_markup=builder.as_markup(resize_keyboard=True))

async def get_question(message, user_id):
    current_question_index = await get_quiz_index(user_id)
    correct_index = quiz_data[current_question_index]['correct_option']
    opts = quiz_data[current_question_index]['options']
    kb = generate_options_keyboard(opts, opts[int(correct_index)])
    await message.answer(f"{quiz_data[current_question_index]['question']}", reply_markup=kb)


async def new_quiz(message):
    user_id = message.from_user.id
    current_question_index = 0
    correct_qiz_ansver = 0
    await update_quiz_index(user_id, current_question_index, correct_qiz_ansver)
    await get_question(message, user_id)


async def get_quiz_index(user_id):
     # Подключаемся к базе данных
     async with aiosqlite.connect(DB_NAME) as db:
        # Получаем запись для заданного пользователя
        async with db.execute('SELECT question_index FROM quiz_state WHERE user_id = (?)', (user_id, )) as cursor:
            # Возвращаем результат
            results = await cursor.fetchone()
            if results is not None:
                return results[0]
            else:
                return 0
            
async def get_quiz_ansver(user_id):
     # Подключаемся к базе данных
     async with aiosqlite.connect(DB_NAME) as db:
        # Получаем запись для заданного пользователя
        async with db.execute('SELECT quiz_ansver FROM quiz_state WHERE user_id = (?)', (user_id, )) as cursor:
            # Возвращаем результат
            results = await cursor.fetchone()
            if results is not None:
                return results[0]
            else:
                return 0


async def update_quiz_index(user_id, index, ansver):
    # Создаем соединение с базой данных (если она не существует, она будет создана)
    async with aiosqlite.connect(DB_NAME) as db:
        # Вставляем новую запись или заменяем ее, если с данным user_id уже существует
        await db.execute('INSERT OR REPLACE INTO quiz_state (user_id, question_index, quiz_ansver) VALUES (?, ?, ?)', (user_id, index, ansver))
        # Сохраняем изменения
        await db.commit()

async def get_user_nickname(chat_id, user_id): 
    chat_member = await bot.get_chat_member(chat_id, user_id) 
    return chat_member.user.username
    
# Хэндлер на команду /quiz
@dp.message(F.text=="Начать игру")
@dp.message(Command("quiz"))
async def cmd_quiz(message: types.Message):

    await message.answer(f"Давайте начнем квиз!")
    await new_quiz(message)

@dp.message(F.text=="результат")
@dp.message(Command("rez"))
async def cmd_rez(message: types.Message):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id FROM quiz_state") as name:
            i=0
            N=[]
            while True:
                name_row = await name.fetchone()
                #chat_id = name_row[0]
                if name_row:
                    nic = await get_user_nickname(name_row[0], name_row[0])
                    N.append(nic)
                else:
                    break                
        async with db.execute("SELECT quiz_ansver FROM quiz_state") as cursor:
            while True:
                next_row = await cursor.fetchone()
                if next_row:
                    await message.answer(f"Пользователь: {N[i]}, ответил: {next_row[0]}")
                    i+=1
                else:
                    break



async def create_table():
    # Создаем соединение с базой данных (если она не существует, она будет создана)
    async with aiosqlite.connect(DB_NAME) as db:
        # Создаем таблицу
        await db.execute('''CREATE TABLE IF NOT EXISTS quiz_state (user_id INTEGER PRIMARY KEY, question_index INTEGER, quiz_ansver INTEGER)''')
        # Сохраняем изменения
        await db.commit()



# Запуск процесса поллинга новых апдейтов
async def main():

    # Запускаем создание таблицы базы данных
    await create_table()

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
