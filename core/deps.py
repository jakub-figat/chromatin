from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db_session


async def get_db() -> AsyncIterator[AsyncSession]:
    async with get_db_session() as session:
        yield session
