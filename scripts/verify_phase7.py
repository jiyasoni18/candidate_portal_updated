"""
Phase 7 Verification Script

Verifies the agent.py voice worker structural layer without requiring a live
LiveKit server or any AI provider credentials.

Asserts:
  - _build_system_prompt returns a string containing the candidate name,
    job title, and all 8 question texts from the fixture metadata
  - The system prompt does not contain any banned buzzwords
  - entrypoint is an async coroutine function

Usage:
    python scripts/verify_phase7.py
"""

import asyncio
import os
import sys

# Ensure the project root is on sys.path when running from the scripts/ subdirectory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _section(title: str) -> None:
    print(f"\n{'='*60}")
    print(title)
    print(f"{'='*60}")


def _pass(msg: str) -> None:
    print(f"[PASS] {msg}")


def _fail(msg: str) -> None:
    print(f"[FAIL] {msg}")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Fixture data
# ---------------------------------------------------------------------------

FIXTURE_CANDIDATE_NAME = "Jane Smith"
FIXTURE_JOB_TITLE = "Senior Python Engineer"
FIXTURE_RESUME_SUMMARY = {
    "skills": ["Python", "FastAPI", "PostgreSQL"],
    "experience_years": 5,
}
FIXTURE_JD_SUMMARY = "We are looking for a Python engineer with async experience."
FIXTURE_QUESTIONS = [
    {"question": f"Question number {i}: tell me about topic {i}."}
    for i in range(1, 9)
]

BANNED_BUZZWORDS = [
    "spearheaded",
    "honed",
    "leveraged",
    "cross-functional",
    "robust",
    "deep dive",
]


# ---------------------------------------------------------------------------
# Main verification
# ---------------------------------------------------------------------------

def main() -> None:
    # -----------------------------------------------------------------------
    # Step 1: Import _build_system_prompt from agent
    # -----------------------------------------------------------------------
    _section("STEP 1: Importing _build_system_prompt from agent")

    try:
        from agent import _build_system_prompt
        _pass("_build_system_prompt imported successfully")
    except ImportError as exc:
        _fail(f"Failed to import _build_system_prompt: {exc}")

    # -----------------------------------------------------------------------
    # Step 2: Run prompt builder with fixture data
    # -----------------------------------------------------------------------
    _section("STEP 2: Building system prompt with fixture metadata")

    try:
        prompt = _build_system_prompt(
            candidate_name=FIXTURE_CANDIDATE_NAME,
            job_title=FIXTURE_JOB_TITLE,
            resume_summary=FIXTURE_RESUME_SUMMARY,
            questions=FIXTURE_QUESTIONS,
            jd_summary=FIXTURE_JD_SUMMARY,
        )
        _pass("_build_system_prompt returned without error")
    except Exception as exc:
        _fail(f"_build_system_prompt raised an exception: {exc}")

    # -----------------------------------------------------------------------
    # Step 3: Assert prompt contains candidate name and job title
    # -----------------------------------------------------------------------
    _section("STEP 3: Asserting candidate name and job title are present")

    if FIXTURE_CANDIDATE_NAME not in prompt:
        _fail(f"Prompt missing candidate name: '{FIXTURE_CANDIDATE_NAME}'")
    _pass(f"Prompt contains candidate name: '{FIXTURE_CANDIDATE_NAME}'")

    if FIXTURE_JOB_TITLE not in prompt:
        _fail(f"Prompt missing job title: '{FIXTURE_JOB_TITLE}'")
    _pass(f"Prompt contains job title: '{FIXTURE_JOB_TITLE}'")

    # -----------------------------------------------------------------------
    # Step 4: Assert all 8 question texts are present
    # -----------------------------------------------------------------------
    _section("STEP 4: Asserting all 8 question texts are present in prompt")

    for i, q in enumerate(FIXTURE_QUESTIONS, start=1):
        question_text = q["question"]
        if question_text not in prompt:
            _fail(f"Prompt missing question {i}: '{question_text}'")
        _pass(f"Question {i} found in prompt")

    # -----------------------------------------------------------------------
    # Step 5: Assert no banned buzzwords appear in the dynamic content sections
    # (The constraint section intentionally lists them as banned — we check
    #  that they don't appear in the candidate profile or question roadmap.)
    # -----------------------------------------------------------------------
    _section("STEP 5: Asserting no banned buzzwords appear in dynamic content sections")

    # Extract only the lines before the Interaction Constraints section
    constraints_marker = "# Interaction Constraints"
    dynamic_section = prompt.split(constraints_marker)[0] if constraints_marker in prompt else prompt
    dynamic_lower = dynamic_section.lower()

    for word in BANNED_BUZZWORDS:
        if word.lower() in dynamic_lower:
            _fail(f"Banned buzzword found in dynamic content sections: '{word}'")
        _pass(f"Banned buzzword absent from dynamic content: '{word}'")

    # -----------------------------------------------------------------------
    # Step 6: Assert entrypoint is an async coroutine function
    # -----------------------------------------------------------------------
    _section("STEP 6: Asserting entrypoint is an async coroutine function")

    try:
        from agent import entrypoint
        _pass("entrypoint imported successfully")
    except ImportError as exc:
        _fail(f"Failed to import entrypoint: {exc}")

    if not asyncio.iscoroutinefunction(entrypoint):
        _fail("entrypoint is NOT an async coroutine function")
    _pass("entrypoint is confirmed as an async coroutine function")

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    print(f"\n{'='*60}")
    print("Phase 7 verification PASSED.")
    print(f"  candidate : {FIXTURE_CANDIDATE_NAME}")
    print(f"  job_title : {FIXTURE_JOB_TITLE}")
    print(f"  questions : {len(FIXTURE_QUESTIONS)} fixture questions verified")
    print(f"  buzzwords : {len(BANNED_BUZZWORDS)} banned words checked")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
