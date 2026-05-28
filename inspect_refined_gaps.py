import asyncio
import asyncpg
import json

async def main():
    conn = await asyncpg.connect("postgresql://practice_user:practice_password_2026@localhost:5434/interview_practice_db")
    row = await conn.fetchrow("SELECT id, enhanced_analysis, custom_additions FROM practice_sessions ORDER BY created_at DESC LIMIT 1")
    if row:
        print("Session ID:", row['id'])
        ea = json.loads(row['enhanced_analysis']) if isinstance(row['enhanced_analysis'], str) else row['enhanced_analysis']
        if ea:
            print("refined_gaps_list:", ea.get("refined_gaps_list"))
            print("refined_custom_additions:", ea.get("refined_custom_additions"))
            print("improvements:", ea.get("improvements"))
            print("selected_improvements:", ea.get("selected_improvements"))
        else:
            print("enhanced_analysis is NULL")
    await conn.close()

asyncio.run(main())
