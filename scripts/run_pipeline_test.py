import asyncio
import logging

logging.basicConfig(level=logging.INFO)

from services.background_pipeline import process_session_background
import asyncpg
from config import settings


async def main():
    pool = await asyncpg.create_pool(dsn=settings.DATABASE_URL)
    await process_session_background(
        "544c545d-475d-4b16-9630-9268eb0a0aa5",
        "06b202b9-b480-4e05-9d6f-6508f71c301e",
        "./storage/resumes/544c545d-475d-4b16-9630-9268eb0a0aa5/resume.pdf",
        pool,
    )
    await pool.close()
    print("Pipeline complete")


asyncio.run(main())
