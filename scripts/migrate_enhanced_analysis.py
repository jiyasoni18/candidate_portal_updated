import asyncio
import asyncpg

async def migrate():
    conn = await asyncpg.connect(
        "postgresql://practice_user:practice_password_2026@localhost:5434/interview_practice_db"
    )
    await conn.execute("""
        ALTER TABLE practice_sessions
        ADD COLUMN IF NOT EXISTS enhanced_analysis JSONB,
        ADD COLUMN IF NOT EXISTS custom_additions TEXT,
        ADD COLUMN IF NOT EXISTS improved_pdf_url VARCHAR(500)
    """)
    print("Migration complete — enhanced_analysis, custom_additions, and improved_pdf_url columns added.")
    await conn.close()

asyncio.run(migrate())
