import asyncio
import asyncpg
from services.orchestrator import process_session_background
from config import settings
from dotenv import load_dotenv

load_dotenv()

async def run():
    # Connect and get a pool for the orchestrator
    pool = await asyncpg.create_pool(settings.DATABASE_URL)
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT id, job_id, resume_url FROM practice_sessions WHERE status='parsing' ORDER BY created_at DESC LIMIT 1")
        if not row:
            print("No sessions stuck in parsing state.")
            return
        session_id, job_id, resume_url = row['id'], row['job_id'], row['resume_url']
    
    file_path = resume_url if resume_url.startswith('./') else './' + resume_url
    print(f"Recovering session {session_id} ...")
    
    # Rerun process
    await process_session_background(str(session_id), str(job_id), file_path, pool)
    
    print("Done recovering session.")
    await pool.close()

asyncio.run(run())
