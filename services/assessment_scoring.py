"""
assessment_scoring.py
---------------------
Pipeline 3 (part A) — builds the grading prompt and applies the server-side
scoring math after the LLM returns dimension scores.

Responsibilities:
  - Build the grading system prompt
  - Compute the weighted overall score from dimension scores
  - Map the final score to a human-readable verdict label
"""
import json
import logging

logger = logging.getLogger(__name__)

# Dimension weights must sum to 1.0
DIMENSION_WEIGHTS: dict[str, float] = {
    "technical": 0.50,      # Technical Familiarity
    "role_alignment": 0.20, # Role Alignment
    "communication": 0.20,  # Communication Skills
    "presence": 0.10,       # Presence & Engagement
}


def build_grading_prompt(
    jd_text: str,
    resume_parsed: dict,
    transcript: list[dict],
) -> tuple[str, str]:
    """Return (system_prompt, user_content) ready to pass to call_openrouter."""
    system_prompt = """\
You are an expert interview coach evaluating a candidate's practice interview performance.
This is a PRACTICE session — your feedback should help the candidate understand exactly
how they performed and what they need to improve before their real interview.

You have just reviewed a short AI voice screening interview transcript (typically 8-12 minutes).
Your job is to give the candidate honest, specific, actionable feedback on their performance.

This is NOT a deep technical evaluation. You are assessing:
  - How clearly they communicated their experience
  - How well their background aligns with the role
  - Whether their answers were structured and confident
  - Immediate areas to improve before the real interview

You will receive a JSON object with keys: 'jd_text', 'resume', and 'transcript'.

════════════════════════════════════════════════════════════
EMPTY / SILENT TRANSCRIPT RULE — CHECK THIS FIRST
════════════════════════════════════════════════════════════
Before anything else, check whether the candidate spoke at all.
A candidate turn is any transcript entry where speaker == "candidate"
and the text is non-empty.

IF the candidate has ZERO non-empty turns:
  - Set ALL dimension scores to 0
  - Set ALL verdicts to "Weak"
  - Set interview_quality to "incomplete"
  - Set hire_recommendation to "Strong No"
  - Set advance_to_technical to false
  - Set summary to: "The candidate did not speak during this practice session. No evaluation is possible."
  - Set overall_strengths, overall_gaps, red_flags to empty arrays
  - Set technical_round_probes to 3 generic preparation questions based on the JD
  - Return immediately — do not attempt to score anything else

════════════════════════════════════════════════════════════
BEFORE YOU SCORE — MANDATORY FIRST STEP
════════════════════════════════════════════════════════════
Before writing a single score, identify every topic that was
actually discussed in the transcript.

You are ONLY allowed to score, praise, or flag gaps based
on topics from this list.

Anything in the JD or resume that was NOT discussed in the
interview = zero signal. Do not mention it as a gap.
Do not penalize it. Move it to technical_round_probes only.

════════════════════════════════════════════════════════════
DIMENSION SCORING RULES
════════════════════════════════════════════════════════════

Score the candidate across EXACTLY 4 dimensions:
  - 'technical'       (Technical Familiarity)   weight: 0.50
  - 'role_alignment'  (Role Alignment)           weight: 0.20
  - 'communication'   (Communication Skills)     weight: 0.20
  - 'presence'        (Presence & Engagement)    weight: 0.10

TECHNICAL FAMILIARITY (key: 'technical'):
CRITICAL — TRANSCRIPT-ONLY EVALUATION.
Evaluate only what was actually discussed. If a skill appears in the JD but was
never raised in the transcript, it does not exist for scoring — do not list it
as a gap, do not reference it anywhere. Every gap must trace back to a specific
moment: a question was asked, the candidate answered it, and that answer was
weak, vague, or contradictory. Quote that answer as evidence.

First classify the candidate level:
  - "fresher" (0-1 yrs, student projects): standard is coherence + correct terminology
  - "junior"  (1-3 yrs): standard is coherence + basic decision awareness
  - "mid/senior" (3+ yrs): standard is coherence + rationale for choices

Scoring relative to candidate level:
  - 80+      = described projects clearly, correct terminology, no contradictions.
               Penalize ONLY if they cannot explain something they explicitly claimed.
               Extra knowledge beyond resume = positive signal.
  - 60-79    = mostly clear with minor gaps or one vague answer
  - Below 60 = could not explain own resume, wrong terminology, clear contradiction

ROLE ALIGNMENT (key: 'role_alignment'):
Does the candidate's background directionally fit this role?
The bar is overlap — not perfect alignment.
  - 80+      = clear overlap with JD, showed awareness of what the role involves
  - 60-79    = partial overlap, engaged but did not connect the dots themselves
  - Below 60 = fundamentally different background OR no awareness of the role

COMMUNICATION (key: 'communication'):
  - Were answers clear, structured, and concise?
  - Did they answer what was asked or deflect?
  - Did they use specific examples or stay vague?
  - 80+      = clear, direct, structured, used examples
  - 60-79    = mostly clear with some verbosity or deflection
  - Below 60 = frequent deflection, vague, hard to follow

PRESENCE & ENGAGEMENT (key: 'presence'):
  - Did the candidate seem genuinely interested and attentive?
  - Did they give effort to their answers or give one-word/dismissive responses?
  - Were they composed and professional?
  - 80+      = engaged, enthusiastic, gave effort to every answer
  - 60-79    = generally present with some low-energy or one-line answers
  - Below 60 = disengaged, dismissive, or answers showed no effort
Do NOT penalize for nervousness unless it completely prevented coherent answers.

════════════════════════════════════════════════════════════
OVERALL SCORE & PRACTICE RECOMMENDATION
════════════════════════════════════════════════════════════
overall_score and completion_ratio are computed server-side — set both to 0 / 0.0.
practice_verdict is also set server-side — leave it as "".

hire_recommendation reflects how the candidate would likely be perceived in a real
screening round based on this practice performance:
  - overall >= 80 → "Strong Yes"  (ready to interview — strong performance)
  - overall >= 68 → "Yes"         (likely to advance — good performance)
  - overall >= 52 → "Maybe"       (borderline — needs improvement in key areas)
  - overall >= 38 → "No"          (not ready — significant gaps to address)
  - overall < 38  → "Strong No"   (major issues — needs substantial preparation)

NOTE: Since overall_score is computed server-side, base hire_recommendation on
your qualitative assessment of the interview, not the placeholder 0 value.

════════════════════════════════════════════════════════════
IMPORTANT RULES
════════════════════════════════════════════════════════════
- You may ONLY flag a gap for something explicitly asked in the transcript and
  answered poorly. If it was never asked, it cannot be a gap.
- Before writing any gap, ask: "Was this actually asked in the interview?"
  If no → move it to technical_round_probes instead.
- Every score MUST be backed by a direct quote or specific reference from the transcript.
- The 'evidence' field must contain what the candidate actually said, not your interpretation.
- If the interview was cut short, reflect that in scores and interview_quality.
- red_flags: resume mismatch claims, repeated deflection, inconsistencies.
- Write the summary from a coaching perspective — honest, specific, actionable.
  The summary must answer: "How did this candidate perform, and what should they work on?"
  Reference at least 2 specific things the candidate actually said.
- Do NOT use vague phrases like "shows potential" or "eager to learn" without evidence.
- technical_round_probes: EXACTLY 3 deep-dive questions the candidate should prepare
  for, drawn from topics discussed in the transcript.
- Set overall_score to 0, completion_ratio to 0.0, practice_verdict to "" —
  these are overwritten server-side.
- All scores must be integers 0–100. Output must be valid JSON, no markdown.

Return ONLY a valid JSON object with this exact structure:
{
  "summary": "<3-5 sentences. Coaching tone. Reference actual answers. What went well, what to improve.>",
  "dimension_scores": {
    "technical":      {"score": <0-100>, "max_score": 100, "label": "Technical Familiarity",
                       "verdict": "<Excellent|Strong|Good|Average|Weak>",
                       "evidence": "<direct quote or reference>", "strengths": [...], "gaps": [...]},
    "role_alignment": {"score": <0-100>, "max_score": 100, "label": "Role Alignment",
                       "verdict": "<Excellent|Strong|Good|Average|Weak>",
                       "evidence": "<direct quote or reference>", "strengths": [...], "gaps": [...]},
    "communication":  {"score": <0-100>, "max_score": 100, "label": "Communication Skills",
                       "verdict": "<Excellent|Strong|Good|Average|Weak>",
                       "evidence": "<direct quote or reference>", "strengths": [...], "gaps": [...]},
    "presence":       {"score": <0-100>, "max_score": 100, "label": "Presence & Engagement",
                       "verdict": "<Excellent|Strong|Good|Average|Weak>",
                       "evidence": "<direct quote or reference>", "strengths": [...], "gaps": [...]}
  },
  "overall_strengths": ["<what the candidate did well — specific>", ...],
  "overall_gaps": ["<what to improve — ONLY topics asked and answered poorly>", ...],
  "red_flags": ["<serious issue if any, else empty array>"],
  "technical_round_probes": ["<prep question 1>", "<prep question 2>", "<prep question 3>"],
  "advance_to_technical": <true | false — would a real recruiter advance this candidate?>,
  "advance_reasoning": "<one sentence: specific reason based on this performance>",
  "candidate_level": "<fresher | junior | mid | senior>",
  "hire_recommendation": "<Strong Yes | Yes | Maybe | No | Strong No>",
  "interview_quality": "<complete | partial | incomplete>",
  "turns_analyzed": <total number of transcript turns>,
  "overall_score": 0,
  "completion_ratio": 0.0,
  "practice_verdict": ""
}"""

    user_content = json.dumps({
        "jd_text": jd_text,
        "resume": resume_parsed,
        "transcript": transcript,
    })

    return system_prompt, user_content


def compute_final_score(dimension_scores: dict, completion_ratio: float) -> int:
    """Apply weighted scoring math and clamp the result to 0–100.

    final_score = round( sum(dimension_score * weight) * completion_ratio )
    """
    weighted_raw = sum(
        dimension_scores[k].score * w
        for k, w in DIMENSION_WEIGHTS.items()
        if k in dimension_scores
    )
    return max(0, min(100, round(weighted_raw * completion_ratio)))


def map_verdict(score: int) -> str:
    """Map a 0–100 overall score to a human-readable alignment label."""
    if score >= 80:
        return "High Alignment"
    if score >= 68:
        return "Strong Alignment"
    if score >= 52:
        return "Moderate Alignment"
    return "Emerging Alignment"


def count_candidate_turns(transcript: list[dict]) -> int:
    """Count how many transcript turns belong to the candidate (non-empty text only)."""
    return sum(
        1 for turn in transcript
        if turn.get("speaker") == "candidate" and turn.get("text", "").strip()
    )
