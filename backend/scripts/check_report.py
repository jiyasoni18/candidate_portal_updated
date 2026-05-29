import asyncio
import asyncpg
import json
from config import settings


async def main():
    pool = await asyncpg.create_pool(dsn=settings.DATABASE_URL)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT resume_report FROM practice_sessions WHERE id=$1",
            "544c545d-475d-4b16-9630-9268eb0a0aa5",
        )
        report = json.loads(row["resume_report"]) if isinstance(row["resume_report"], str) else row["resume_report"]
        print(json.dumps(report, indent=2))
    await pool.close()


asyncio.run(main())
