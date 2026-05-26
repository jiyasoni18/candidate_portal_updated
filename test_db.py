import asyncio
import asyncpg
from config import settings
from uuid import uuid4

async def test_db():
    try:
        pool = await asyncpg.create_pool(dsn=settings.DATABASE_URL)
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id FROM users LIMIT 1"
            )
            print("Users:", row)
            if row:
                uid = row["id"]
                print("UUID type:", type(uid))
                
                # Add missing columns safely
                try:
                    await conn.execute("""
                        ALTER TABLE practice_sessions ADD COLUMN IF NOT EXISTS enhanced_analysis JSONB;
                        ALTER TABLE practice_sessions ADD COLUMN IF NOT EXISTS custom_additions TEXT;
                        ALTER TABLE practice_sessions ADD COLUMN IF NOT EXISTS improved_pdf_url VARCHAR(500);
                    """)
                    print("Successfully added missing columns.")
                except Exception as e:
                    print("Failed to add missing columns:", type(e), e)
                    
        await pool.close()
    except Exception as e:
        print("Pool failed:", e)

if __name__ == "__main__":
    asyncio.run(test_db())
