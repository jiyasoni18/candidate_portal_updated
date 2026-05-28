import asyncio
from services.enhanced_analyzer import generate_ats_pdf

async def main():
    try:
        buffer = await generate_ats_pdf(
            resume_text="Hello World",
            accepted_texts="Some gaps",
            improvements_text="Some improvements",
            custom_text="Custom",
            jd_text="Software Engineer",
            template_name="Two-Column Professional"
        )
        print("Success, length:", len(buffer.getvalue()))
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(main())
