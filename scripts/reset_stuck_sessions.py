import asyncio
import asyncpg

async def reset():
    conn = await asyncpg.connect(
        "postgresql://practice_user:practice_password_2026@localhost:5434/interview_practice_db"
    )
    result = await conn.execute(
        "UPDATE practice_sessions SET status='ready_to_start', livekit_room_name=NULL WHERE status='interviewing'"
    )
    print("Reset result:", result)
    
    rows = await conn.fetch("SELECT id, status FROM practice_sessions ORDER BY created_at DESC LIMIT 5")
    for r in rows:
        print(f"  {r['id']} -> {r['status']}")
    
    await conn.close()

asyncio.run(reset())
