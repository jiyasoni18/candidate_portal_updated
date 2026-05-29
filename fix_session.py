import asyncio
import asyncpg
import json
from services.enhanced_analyzer import analyze_resume_enhanced
from config import settings
from dotenv import load_dotenv

load_dotenv()

async def run():
    conn = await asyncpg.connect('postgresql://practice_user:practice_password_2026@localhost:5434/interview_practice_db')
    row = await conn.fetchrow("SELECT id, resume_text, job_id FROM practice_sessions ORDER BY created_at DESC LIMIT 1")
    session_id, resume_text, job_id = row['id'], row['resume_text'], row['job_id']
    job_row = await conn.fetchrow("SELECT description FROM practice_jobs WHERE id=$1", job_id)
    jd_text = job_row['description']

    try:
        print("Running enhanced analysis...")
        res = await analyze_resume_enhanced(resume_text, jd_text, model_name="google/gemini-2.0-flash-001")
        print("Finished successfully")
        
        await conn.execute("UPDATE practice_sessions SET enhanced_analysis=$1 WHERE id=$2", json.dumps(res), session_id)
        print("Updated DB")
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

asyncio.run(run())
