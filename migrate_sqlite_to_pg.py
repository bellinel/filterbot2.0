import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from database.engine import Base, Message, Reklama_filter, NeRelevant_filter  # твои модели

# SQLite источник
sqlite_engine = create_async_engine("sqlite+aiosqlite:///bot.db", echo=False)
sqlite_session = sessionmaker(sqlite_engine, class_=AsyncSession, expire_on_commit=False)

# PostgreSQL получатель
pg_engine = create_async_engine(
    "postgresql+asyncpg://mybotuser:mysecurepassword@localhost:5432/mybotdb", echo=True
)
pg_session = sessionmaker(pg_engine, class_=AsyncSession, expire_on_commit=False)

tables = [Message, Reklama_filter, NeRelevant_filter]

async def migrate_table(table_cls):
    print(f"🔄 Миграция таблицы {table_cls.__tablename__}...")
    async with sqlite_session() as src, pg_session() as dst:
        result = await src.execute(select(table_cls))
        rows = result.scalars().all()
        for row in rows:
            # создаем новый экземпляр для PostgreSQL
            new_row = table_cls(**row.__dict__)
            dst.add(new_row)
        await dst.commit()
    print(f"✅ Готово: {table_cls.__tablename__} ({len(rows)} записей)")

async def main():
    # Создаем таблицы в PostgreSQL
    async with pg_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Миграция данных
    for table in tables:
        await migrate_table(table)

    await pg_engine.dispose()
    await sqlite_engine.dispose()
    print("🎉 Миграция завершена")

if __name__ == "__main__":
    asyncio.run(main())
