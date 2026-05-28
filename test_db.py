import asyncio
import asyncpg
import json

async def main():
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:5432/candidate_practice")
    row = await conn.fetchrow("SELECT user_id, enhanced_analysis, custom_additions FROM practice_sessions WHERE id = 'f50403f6-3bc9-49c4-809f-9d4bc29b2e91'")
    if row:
        print("Found session!")
        print("enhanced_analysis gaps:", json.loads(row['enhanced_analysis']).get('gaps', []))
    else:
        print("Session not found")
        
    await conn.close()

asyncio.run(main())
