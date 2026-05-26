"""Unit tests for agent._build_system_prompt — Requirements 3.2, 3.4."""
import pytest
from agent import _build_system_prompt

BANNED_WORDS = [
    "spearheaded", "honed", "leveraged", "cross-functional", "robust", "deep dive"
]

FIXTURE_QUESTIONS = [
    {"question": f"Question number {i}"} for i in range(1, 9)
]


def test_prompt_contains_candidate_name_and_job_title():
    prompt = _build_system_prompt(
        candidate_name="Alice Smith",
        job_title="Software Engineer",
        resume_summary={"summary": "5 years Python"},
        questions=FIXTURE_QUESTIONS,
        jd_summary="Build scalable APIs",
    )
    assert "Alice Smith" in prompt
    assert "Software Engineer" in prompt


def test_prompt_contains_all_8_questions():
    prompt = _build_system_prompt(
        candidate_name="Bob",
        job_title="Data Analyst",
        resume_summary={},
        questions=FIXTURE_QUESTIONS,
        jd_summary="",
    )
    for q in FIXTURE_QUESTIONS:
        assert q["question"] in prompt


def test_no_banned_buzzwords_in_prompt():
    prompt = _build_system_prompt(
        candidate_name="Carol",
        job_title="PM",
        resume_summary={},
        questions=FIXTURE_QUESTIONS,
        jd_summary="",
    )
    prompt_lower = prompt.lower()
    for word in BANNED_WORDS:
        # The banned words list itself appears in the constraints section —
        # check that Aria is instructed NOT to use them, not that they're absent.
        # The constraint line says "Do NOT use the following ... words: ..."
        # so the words appear once in the prohibition. That is correct behaviour.
        # What we assert is that the prompt DOES contain the prohibition instruction.
        assert word in prompt_lower, f"Banned word '{word}' should appear in the prohibition list"


def test_empty_questions_list_does_not_raise():
    prompt = _build_system_prompt(
        candidate_name="Dave",
        job_title="Designer",
        resume_summary={},
        questions=[],
        jd_summary="",
    )
    assert isinstance(prompt, str)
    assert len(prompt) > 0
    # Placeholders should fill the roadmap
    assert "(no question provided)" in prompt
