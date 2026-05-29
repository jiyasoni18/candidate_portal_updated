import asyncio
import asyncpg

async def check():
    conn = await asyncpg.connect(
        "postgresql://practice_user:practice_password_2026@localhost:5434/interview_practice_db"
    )
    rows = await conn.fetch(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_name='practice_sessions' ORDER BY ordinal_position"
    )
    for r in rows:
        print(f"  {r['column_name']}: {r['data_type']}")
    await conn.close()

asyncio.run(check())
