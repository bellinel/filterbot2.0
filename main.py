# Импортируем патч для модуля inspect
import inspect_patch



import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
import os
from aiogram.filters.command import Command
from database.engine import Database
from database.orm import MessageRepository
from filter import filter_router
import datetime
from keyboard import clean_day_kb, menu_kb
from aiogram.fsm.state import State, StatesGroup
    

load_dotenv()


bot = Bot(token=os.getenv("BOT_TOKEN"))
# Создаем хранилище состояний в памяти

# Передаем хранилище состояний при создании диспетчера
dp = Dispatcher()

# Получаем количество дней до очистки из переменной окружения
# Если переменная не задана, используем 7 дней по умолчанию
DB_CLEANUP_DAYS = int(os.getenv("DB_CLEANUP_DAYS", 7))

# Глобальная переменная для хранения задачи очистки
cleanup_task = None


logging.basicConfig(level=logging.INFO)

dp.include_router(filter_router)

class Clean(StatesGroup):
    clean_day = State()



@dp.message(Command("id"))
async def start_command(message: types.Message):
    await message.answer(f"Ваш ID: {message.chat.id}")

@dp.message(Command("cleanup_info"))
async def cleanup_info_command(message: types.Message):
    """Команда для получения информации о периоде очистки базы данных"""
    await message.answer(f"База данных сообщений очищается каждые {DB_CLEANUP_DAYS} дней")


@dp.callback_query(F.data == 'dubli')
async def dubli(callback: types.CallbackQuery):
    await callback.message.edit_text(text=f'Период хранения составляет: {DB_CLEANUP_DAYS} days', reply_markup=await clean_day_kb())


@dp.callback_query(F.data == 'clean_day')
async def clean_day(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(text=f'Введите количество дней')
    await state.set_state(Clean.clean_day)


@dp.message(Clean.clean_day)
async def set_cleanup_days_command(message: types.Message, state : FSMContext):
    """Команда для установки периода очистки базы данных (только для администратора)"""
    # Проверяем, что сообщение содержит аргумент - число дней
    args = message.text
    args = int(args)
    if type(args) is not  int:
        await message.answer("Количество дней должно быть числом")
        return
    
    try:
        days = args
        if days < 1:
            await message.answer("Количество дней должно быть положительным числом")
            return
            
        # Здесь можно добавить проверку прав администратора
        # if message.from_user.id != 192659790: return
        
        # Записываем новое значение в .env файл
        with open(".env", "r") as f:
            env_lines = f.readlines()
        
        # Ищем строку с DB_CLEANUP_DAYS или добавляем новую
        found = False
        for i, line in enumerate(env_lines):
            if line.startswith("DB_CLEANUP_DAYS="):
                env_lines[i] = f"DB_CLEANUP_DAYS={days}\n"
                found = True
                break
        
        if not found:
            env_lines.append(f"DB_CLEANUP_DAYS={days}\n")
        
        # Записываем обновленный файл
        with open(".env", "w") as f:
            f.writelines(env_lines)
        
        # Обновляем глобальное значение
        global DB_CLEANUP_DAYS
        DB_CLEANUP_DAYS = days
        
        # Перезапускаем задачу очистки базы данных с новым интервалом
        restart_cleanup_task()
        
        a = await message.answer(f"Период очистки базы данных установлен на {days} дней. Задача очистки перезапущена с новым интервалом.")
        await asyncio.sleep(3)
        await a.edit_text('Меню бота', reply_markup=await menu_kb())
        logging.info(f"Период очистки базы данных изменен на {days} дней пользователем {message.from_user.id}. Задача перезапущена.")
        await state.clear()
    except ValueError:
        await message.answer("Ошибка: укажите корректное целое число дней")

# Перезапуск задачи очистки базы данных
def restart_cleanup_task():
    global cleanup_task
    
    # Если задача уже существует, отменяем её
    if cleanup_task and not cleanup_task.done():
        logging.info("Отмена текущей задачи очистки базы данных")
        cleanup_task.cancel()
    
    # Создаем новую задачу очистки
    cleanup_task = asyncio.create_task(schedule_db_cleaning())
    logging.info(f"Задача очистки базы данных перезапущена с интервалом {DB_CLEANUP_DAYS} дней")

# Функция для очистки базы данных
async def schedule_db_cleaning():
    """Планирует и выполняет очистку базы данных с заданным интервалом"""
    # Получаем доступ к глобальной переменной db
    db = Database()
    
    # Создаем репозиторий для работы с сообщениями
    message_repo = MessageRepository(db)
    
    try:
        while True:
            # Получаем актуальное значение дней для очистки
            days = DB_CLEANUP_DAYS
            # Вычисляем время в секундах
            # cleanup_seconds = days * 24 * 60 * 60  # дни * 24 часа * 60 минут * 60 секунд
            cleanup_seconds = 10
            
            # Логируем информацию о планируемой очистке
            next_clean_date = datetime.datetime.now() + datetime.timedelta(days=days)
            logging.info(f"Следующая очистка базы данных запланирована на: {next_clean_date} (через {days} дней)")
            
            # Ждем указанное количество дней
            await asyncio.sleep(cleanup_seconds)
            
            # Очищаем базу данных
            try:
                await message_repo.clear_database()
                logging.info(f"База данных успешно очищена: {datetime.datetime.now()}")
            except Exception as e:
                logging.error(f"Ошибка при очистке базы данных: {e}")
                
    except asyncio.CancelledError:
        # Задача была отменена
        logging.info("Задача очистки базы данных отменена")
    except Exception as e:
        logging.error(f"Ошибка в задаче очистки базы данных: {e}")

# Функция запуска бота
async def main():
    db = Database()
    await db.init()
    
    # Выводим информацию о настройках очистки при запуске
    logging.info(f"Установлен период очистки базы данных: {DB_CLEANUP_DAYS} дней")
    
    # Запускаем задачу очистки базы данных в фоновом режиме
    restart_cleanup_task()
    
    # Запускаем бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
