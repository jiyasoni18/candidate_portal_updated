import asyncio
from services.enhanced_analyzer import reanalyze_gaps

async def main():
    resume_text = "Software Engineer"
    jd_text = "Need React, Node, AWS, Docker."
    custom_additions = "I like eating pizza."
    original_gaps_text = "Gap 0: React\nGap 1: Node\nGap 2: AWS\nGap 3: Docker"
    
    res = await reanalyze_gaps(
        resume_text=resume_text,
        jd_text=jd_text,
        custom_additions=custom_additions,
        original_gaps_text=original_gaps_text
    )
    print("REMAINING:", res)

asyncio.run(main())
