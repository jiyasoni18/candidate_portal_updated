import asyncio
import os
from services.enhanced_analyzer import reanalyze_gaps

async def main():
    resume_text = "I am a software engineer."
    jd_text = "Looking for AWS and Python."
    custom_additions = "I ate a sandwich today."
    original_gaps_text = "Gap 0: AWS\nGap 1: Python"
    
    res = await reanalyze_gaps(
        resume_text=resume_text,
        jd_text=jd_text,
        custom_additions=custom_additions,
        original_gaps_text=original_gaps_text
    )
    print("REMAINING GAPS:", res)

asyncio.run(main())
