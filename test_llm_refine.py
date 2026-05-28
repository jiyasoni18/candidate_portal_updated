import asyncio
from services.enhanced_analyzer import refine_custom_additions

async def main():
    gaps_data = {
        "0": {
            "gap": "Exposure to cloud platforms (AWS, GCP, Azure): Not found",
            "note": "ADD_TO_PROJECT: Smart parking detection (Tech: AWS) — I have used the AWS for the managment and used there EC2 service"
        }
    }
    try:
        res = await refine_custom_additions(
            gaps_data=gaps_data,
            custom_text="",
            jd_text="Backend Developer role requiring AWS and Python."
        )
        print("Success:", res)
    except Exception as e:
        print("Error during refine_custom_additions:", e)

asyncio.run(main())
