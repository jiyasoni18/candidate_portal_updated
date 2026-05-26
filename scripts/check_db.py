import asyncio
import asyncpg
from config import settings


async def main():
    pool = await asyncpg.create_pool(dsn=settings.DATABASE_URL)
    async with pool.acquire() as conn:
        # Check users table
        users = await conn.fetch("SELECT id, full_name FROM users LIMIT 5")
        print("Users:", [dict(u) for u in users])

        # Check the session detail query directly
        row = await conn.fetchrow(
            """
            SELECT ps.id, ps.status, ps.resume_report IS NOT NULL as has_report,
                   pj.title as job_title
            FROM practice_sessions ps
            INNER JOIN practice_jobs pj ON ps.job_id = pj.id
            WHERE ps.id = $1 AND ps.user_id = $2
            """,
            "544c545d-475d-4b16-9630-9268eb0a0aa5",
            "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
        )
        print("Session row:", dict(row) if row else "NOT FOUND")
    await pool.close()


asyncio.run(main())
