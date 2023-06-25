from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher, FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


# токен телеграм бота
token_tg = '6241837582:AAGQJE41JcM7BMRTT_HvzNxbeOtkib2EKHI'

# создаем экземпляр бота, диспетчера и памяти
bot = Bot(token_tg)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# создаем движок БД
engine = create_engine('sqlite:///recipes_data.db', echo=True)

# создаем таблицу "recipes" с полями "id", "recipe_name", "how_to_cook"
Base = declarative_base()


class Recipe(Base):
    __tablename__ = 'recipes'
    id = Column(Integer, primary_key=True)
    recipe_name = Column(String)
    how_to_cook = Column(String)


# создаем состояния
class CommandStates(StatesGroup):
    NAME = State()
    HOW_TO_COOK = State()
    EDIT = State()
    DELETE = State()


# создаем таблицу в БД
Base.metadata.create_all(engine)

# создаем сессию для взаимодействия с БД
Session = sessionmaker(bind=engine)
session = Session()


# обработчик команды /start
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    await message.answer('Привет! Я бот для сохранения кулинарных рецептов.\n'
                         'Вы можете сохранять, просматривать, редактировать и удалять свои рецепты.')


# обработчик команды /addrecipe
@dp.message_handler(commands=['addrecipe'])
async def add_recipe_command(message: types.Message):
    await message.answer('Впишите название вашего рецепта.')
    # устанавливаем состояние
    await CommandStates.NAME.set()


# обработчик сообщений для получения названия рецепта
@dp.message_handler(state=CommandStates.NAME)
async def process_recipe_name(message: types.Message, state: FSMContext):
    recipe_name = message.text
    await message.answer('Добавьте ингредиенты и способ приготовления.')
    recipe = Recipe(recipe_name=recipe_name)
    session.add(recipe)
    # отправляем изменения в БД
    session.commit()
    # сохраняем название рецепта в состоянии
    await state.update_data(recipe_name=recipe_name)
    # устанавливаем состояние
    await CommandStates.HOW_TO_COOK.set()


# обработчик сообщений для получения способа приготовления
@dp.message_handler(state=CommandStates.HOW_TO_COOK)
async def process_how_to_cook(message: types.Message, state: FSMContext):
    how_to_cook = message.text
    data = await state.get_data()
    recipe_name = data.get('recipe_name')
    # получаем последний добавленный рецепт из БД
    recipe = session.query(Recipe).filter_by(recipe_name=recipe_name).first()
    # заполняем поле "how_to_cook" способом приготовления
    recipe.how_to_cook = how_to_cook
    # отправляем изменения в БД
    session.commit()
    await message.answer('Рецепт добавлен.')
    await state.finish()


# обработчик команды /listrecipes
@dp.message_handler(commands=['listrecipes'])
async def list_recipes_command(message: types.Message):
    # получаем все рецепты из БД
    recipes = session.query(Recipe).all()
    if recipes:
        response = 'Список рецептов:\n'
        for recipe in recipes:
            response += f'- {recipe.recipe_name}\n'
        await message.answer(response)
    else:
        await message.answer('Нет сохраненных рецептов.')


# обработчик команды /showrecipe
@dp.message_handler(commands=['showrecipe'])
async def show_recipe_command(message: types.Message):
    await message.answer('Напишите мне название рецепта.')
    # регистрируем следующий обработчик для получения названия рецепта
    dp.register_message_handler(process_recipe_for_show)


# обработчик сообщений для получения названия рецепта для просмотра способа приготовления
async def process_recipe_for_show(message: types.Message):
    recipe_name = message.text
    # получаем рецепт из БД по названию
    recipe = session.query(Recipe).filter_by(recipe_name=recipe_name).first()
    if recipe:
        await message.answer(f'Способ приготовления "{recipe_name}":\n{recipe.how_to_cook}')
    else:
        await message.answer(f'Рецепт "{recipe_name}" не найден.')


# обработчик команды /editrecipe
@dp.message_handler(commands=['editrecipe'])
async def edit_recipe_command(message: types.Message):
    await message.answer('Введите название рецепта для редактирования.')
    # устанавливаем состояние
    await CommandStates.EDIT.set()


# обработчик сообщений для получения названия рецепта для редактирования
@dp.message_handler(state=CommandStates.EDIT)
async def process_recipe_for_edit(message: types.Message, state: FSMContext):
    recipe_name = message.text
    # получаем рецепт из БД по названию
    recipe = session.query(Recipe).filter_by(recipe_name=recipe_name).first()
    if recipe:
        await message.answer('Введите новый способ приготовления для рецепта.')
        # устанавливаем состояние редактирования для данного пользователя
        await state.update_data(recipe=recipe)
        await CommandStates.HOW_TO_COOK.set()
    else:
        await message.answer(f'Рецепт "{recipe_name}" не найден.')
        await state.finish()


# Обработчик сообщений для получения нового способа приготовления для редактирования
@dp.message_handler(state=CommandStates.HOW_TO_COOK)
async def process_new_how_to_cook(message: types.Message, state: FSMContext):
    how_to_cook = message.text
    data = await state.get_data()
    recipe = data.get('recipes')
    recipe.how_to_cook = how_to_cook
    session.commit()
    await message.answer(f'Способ приготовления "{recipe.recipe_name}" был отредактирован.')
    await state.finish()


# обработчик команды /deleterecipe
@dp.message_handler(commands=['deleterecipe'])
async def delete_recipe_command(message: types.Message):
    await message.answer('Введите название рецепта, который хотите удалить.')
    # устанавливаем состояние
    await CommandStates.DELETE.set()


# обработчик сообщений для получения названия рецепта для удаления
@dp.message_handler(state=CommandStates.DELETE)
async def process_recipe_for_delete(message: types.Message, state: FSMContext):
    recipe_name = message.text
    # получаем рецепт из БД
    recipe = session.query(Recipe).filter_by(recipe_name=recipe_name).first()
    if recipe:
        session.delete(recipe)
        session.commit()
        await message.answer(f'Рецепт "{recipe_name}" удален.')
    else:
        await message.answer(f'Рецепт "{recipe_name}" не найден.')
    await state.finish()


executor.start_polling(dp, skip_updates=True)
