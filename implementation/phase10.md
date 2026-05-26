# Phase 10: Performance Evaluation & Completion-Weighted Grading Pipeline

## 1. Objective
Build the post-interview analysis engine executed via FastAPI's native `BackgroundTasks`. This pipeline grades the dialogue transcript text against the target Job Description, computes a completion-weighted final score, and commits the detailed breakdown to the database to reveal the final candidate report card.

## 2. Mathematical Scoring Model
To prevent subjective grading inflation and ensure candidates are penalized for missing questions or cutting practice sessions short, the engine must execute your strict objective completion formula:

$$\text{Weighted Raw Score} = \sum (\text{Dimension Score} \times \text{Weight})$$

$$\text{Completion Ratio} = \frac{\text{Questions Answered}}{\text{Expected Questions}}$$

$$\text{Final Overall Score} = \text{Weighted Raw Score} \times \text{Completion Ratio}$$

---

## 3. Operational Step-by-Step Backend Logic

### 3.1. Pipeline 3: Transcript Evaluation Execution
- **Trigger**: Fired automatically by the completing webhook router from Phase 9.
- **Target LLM**: High-tier complex reasoning engine (Claude 3.5 Sonnet or GPT-4o via OpenRouter).
- **Context Generation**: Feed the LLM the raw user `jd_text`, the `resume_parsed` JSON from Phase 4, and the complete session `transcript` array.

### 3.2. Evaluation Dimensions (0 to 100 points each)
Instruct the LLM to score the candidate strictly using transcript evidence across four core components:
1. **Technical Familiarity (50% Weight)**: Can the candidate explain what they built coherently? Adjust the strictness based on the experience level parsed from their resume. **Strict Constraint**: If a specific skill or tool was not asked about during the conversation, it cannot be flagged as an alignment gap.
2. **Role Alignment (20% Weight)**: Measure direct overlap with the core requirements of the target JD text.
3. **Communication Skills (20% Weight)**: Evaluate answer structure, conciseness, and whether they answered questions directly instead of deflecting.
4. **Presence & Engagement (10% Weight)**: Track total candidate conversational effort, responsiveness, and completeness.

### 3.3. Threshold Mapping & Practice Verdict
Convert the resulting final calculated score into a clear, supportive operational verdict for the practice portal:
- **Score $\ge 80$**: High Alignment (Excellent practice performance)
- **Score $\ge 68$**: Strong Alignment (Ready for a live interview)
- **Score $\ge 52$**: Moderate Alignment (Good baseline, keep practicing)
- **Score $< 52$**: Emerging Alignment (Focus on adding transcript evidence and direct answers)

### 3.4. Technical Probe Generation
Instruct the LLM to generate a customized `technical_round_probes` array containing 3 deep-dive engineering topics. These are tailored strictly to what the candidate discussed in the transcript to help them prepare for a real human technical round.

### 3.5. Final Database Update
Save the validated results payload matching the schema defined in `schemas/assessment.py` into the `practice_sessions.interview_assessment` column, and advance `status` strictly to `'completed'`.

---

## 4. Expected Database JSONB Schema Output Shape
```json
{
  "overall_score": 78,
  "practice_verdict": "Strong Alignment",
  "summary": "John communicated his engineering background effectively...",
  "dimension_scores": {
    "technical": {
      "score": 80,
      "max_score": 100,
      "label": "Technical Familiarity",
      "verdict": "Good",
      "evidence": "Candidate accurately described routing patterns...",
      "strengths": ["FastAPI routing structure knowledge"],
      "gaps": []
    }
  },
  "overall_strengths": ["Direct response structure", "Clear tech stack descriptions"],
  "overall_gaps": ["Did not mention database migration tools explicitly"],
  "technical_round_probes": [
    "Prepare to explain how you handle database connection pooling in local Docker configurations."
  ],
  "turns_analyzed": 16,
  "completion_ratio": 1.0
}


5. Verification Check Constraints
The Kiro agent must verify successful completion by asserting:

Run a transcript verification test containing only 4 answered questions out of 8, and confirm the math engine applies a 0.5 multiplier penalty to the final score.

Confirm that when a session hits 'completed', the frontend polling endpoint instantly exposes the full assessment data without errors.


