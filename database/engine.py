
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, Boolean, String
import os
from sqlalchemy.ext.asyncio import AsyncEngine

Base = declarative_base()


class Database:
    """
    Класс для работы с базой данных.
    
    Attributes:
        db_url (str): URL для подключения к базе данных
        engine: Асинхронный движок SQLAlchemy
        session_factory: Фабрика сессий для создания асинхронных сессий
        logger: Логгер для записи событий базы данных
    """
    
    def __init__(self):
        from dotenv import load_dotenv
        load_dotenv()

        user = os.getenv("DB_USER")
        password = os.getenv("DB_PASS")
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME")

        self.db_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db_name}"
        self.engine = create_async_engine(self.db_url, echo=False)
        self.session_factory = sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        self.logger = logging.getLogger(__name__)
        
    async def init(self):
        """
        Инициализирует базу данных, создавая все необходимые таблицы.
        """
        async with self.engine.begin() as conn:
            # Создаем все таблицы, которые еще не созданы
            await conn.run_sync(Base.metadata.create_all)
            self.logger.info("База данных инициализирована")
    
    async def close(self):
        """
        Закрывает соединение с базой данных.
        """
        await self.engine.dispose()
        self.logger.info("Соединение с базой данных закрыто")




class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    text = Column(String, nullable=False)
    message_id = Column(Integer, nullable=False)


class Reklama_filter(Base):
    __tablename__ = "reklama_filter"

    id = Column(Integer, primary_key=True)
    text = Column(String, nullable=False)
    

class NeRelevant_filter(Base):
    __tablename__ = "ne_relevant_filter"

    id = Column(Integer, primary_key=True)
    text = Column(String, nullable=False)


