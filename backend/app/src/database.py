from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel as PBaseModel

from src.config import settings

# Создание синхронного подключения к базе данных
sync_engine = create_engine(
    url=settings.DATABASE_URL_pg,  # URL подключения, задается в конфигурации
    pool_size=5,                        # Максимум пять одновременных соединений
    max_overflow=10                     # Дополнительные соединения при превышении лимита
)

# Создание фабрики сессий
session_factory = sessionmaker(sync_engine)

# Используем declarative_base для старых версий SQLAlchemy
Base = declarative_base()

class BaseModel(Base):
    """
    Базовый класс для всех ORM-моделей.

    Методы:
        __repr__: Представляет объект в читаемом виде, выводя значения всех колонок таблицы.
    """
    __abstract__ = True  # Указываем, что это абстрактный класс (не будет создавать таблицу)

    def __repr__(self):
        cols = [f"{col}={getattr(self, col)}" for col in self.__table__.columns.keys()]
        return f"<{self.__class__.__name__} {','.join(cols)}>"
