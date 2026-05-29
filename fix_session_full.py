import asyncio
import asyncpg
import json
from services.document_extraction import extract_resume_text
from services.enhanced_analyzer import analyze_resume_enhanced
from config import settings
from dotenv import load_dotenv

load_dotenv()

async def run():
    conn = await asyncpg.connect(settings.DATABASE_URL)
    row = await conn.fetchrow("SELECT id, resume_url, job_id FROM practice_sessions ORDER BY created_at DESC LIMIT 1")
    session_id, resume_url, job_id = row['id'], row['resume_url'], row['job_id']
    job_row = await conn.fetchrow("SELECT description FROM practice_jobs WHERE id=$1", job_id)
    jd_text = job_row['description']

    try:
        print("Extracting resume text from PDF:", resume_url)
        # remove prefix if needed or construct the right path
        # storage root is ./storage/resumes
        file_path = resume_url if resume_url.startswith('./') else './' + resume_url
        resume_text = await extract_resume_text(file_path)
        print("Extracted", len(resume_text), "chars")
        
        print("Running enhanced analysis...")
        res = await analyze_resume_enhanced(resume_text, jd_text, model_name="google/gemini-2.0-flash-001")
        print("Finished successfully. Section scores:", res.get("section_scores"))
        
        await conn.execute("UPDATE practice_sessions SET enhanced_analysis=$1 WHERE id=$2", json.dumps(res), session_id)
        print("Updated DB for session", session_id)
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

asyncio.run(run())
