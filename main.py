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
class AddRecipeStates(StatesGroup):
    NAME = State()
    HOW_TO_COOK = State()


# создаем таблицу в БД
Base.metadata.create_all(engine)

# создаем сессию для взаимодействия с БД
Session = sessionmaker(bind=engine)
session = Session()


# обработчик команды /start
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    await message.answer('Привет! Я бот для сохранения кулинарных рецептов.')


# обработчик команды /addrecipe
@dp.message_handler(commands=['addrecipe'])
async def add_recipe_command(message: types.Message):
    await message.answer('Впишите название вашего рецепта.')
    # устанавливаем состояние
    await AddRecipeStates.NAME.set()


# обработчик сообщений для получения названия рецепта
@dp.message_handler(state=AddRecipeStates.NAME)
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
    await AddRecipeStates.HOW_TO_COOK.set()


# обработчик сообщений для получения способа приготовления
@dp.message_handler(state=AddRecipeStates.HOW_TO_COOK)
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


# Обработчик команды /listrecipes
@dp.message_handler(commands=['listrecipes'])
async def list_recipes_command(message: types.Message):
    # Получаем все рецепты из БД
    recipes = session.query(Recipe).all()
    if recipes:
        response = 'Список рецептов:\n'
        for recipe in recipes:
            response += f'• {recipe.recipe_name}\n'
        await message.answer(response)
    else:
        await message.answer('Нет сохраненных рецептов.')


# Обработчик команды /showrecipe
@dp.message_handler(commands=['showrecipe'])
async def show_recipe_command(message: types.Message):
    await message.answer('Введите название рецепта для просмотра способа приготовления.')
    # Регистрируем следующий обработчик для получения названия рецепта
    dp.register_message_handler(process_recipe_for_show)


# Обработчик сообщений для получения названия рецепта для просмотра способа приготовления
async def process_recipe_for_show(message: types.Message):
    recipe_name = message.text
    # Получаем рецепт из БД по названию
    recipe = session.query(Recipe).filter_by(recipe_name=recipe_name).first()
    if recipe:
        await message.answer(f'Способ приготовления для рецепта "{recipe_name}":\n{recipe.how_to_cook}')
    else:
        await message.answer(f'Рецепт "{recipe_name}" не найден.')


executor.start_polling(dp, skip_updates=True)
