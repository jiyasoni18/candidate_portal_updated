import asyncio
import asyncpg
from config import settings


async def main():
    pool = await asyncpg.create_pool(dsn=settings.DATABASE_URL)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, status, resume_report IS NOT NULL as has_report FROM practice_sessions WHERE id=$1",
            "544c545d-475d-4b16-9630-9268eb0a0aa5",
        )
        print(dict(row))
    await pool.close()


asyncio.run(main())
