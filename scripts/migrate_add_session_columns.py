import asyncio
import asyncpg

async def migrate():
    conn = await asyncpg.connect(
        "postgresql://practice_user:practice_password_2026@localhost:5434/interview_practice_db"
    )
    await conn.execute("""
        ALTER TABLE practice_sessions
        ADD COLUMN IF NOT EXISTS end_reason VARCHAR(50),
        ADD COLUMN IF NOT EXISTS duration_seconds INTEGER
    """)
    print("Migration complete — end_reason and duration_seconds columns added.")
    await conn.close()

asyncio.run(migrate())
