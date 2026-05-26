# Implementation Plan

- [x] 1. Install dependencies and extend config





  - [x] 1.1 Add new config fields to `config.py`


    - Add `LIVEKIT_URL: str`, `OPENAI_API_KEY: str`, `DEEPGRAM_API_KEY: str`, `SARVAM_API_KEY: str` to the `Settings` class
    - All four fields are required (no default) so `pydantic-settings` raises `ValidationError` at startup if missing
    - Add corresponding placeholder entries to `.env` with empty values as documentation
    - _Requirements: 6.2, 6.3_

  - [x] 1.2 Write config validation test


    - Assert `Settings` raises `ValidationError` when `OPENAI_API_KEY` is absent
    - _Requirements: 6.3_

- [x] 2. Implement `_build_system_prompt` helper





  - [x] 2.1 Create `agent.py` with the pure prompt builder function


    - Create `agent.py` at the project root
    - Implement `_build_system_prompt(candidate_name, job_title, resume_summary, questions, jd_summary) -> str`
    - Prompt must include: Role/Core Directive section (Aria persona), Candidate Profile section, Fixed Interview Roadmap (numbered 1–8), Interaction Constraints section (sequential delivery, follow-up rules, banned buzzwords list)
    - Use `.get("question", "")` on each question dict to safely extract question text
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [x] 2.2 Write unit tests for `_build_system_prompt`


    - Test that output contains candidate name, job title, and all 8 question strings
    - Test that none of the banned buzzwords appear in the output
    - Test graceful handling of an empty `questions` list
    - _Requirements: 3.2, 3.4_

- [x] 3. Implement `start_mock_interview` and `entrypoint`





  - [x] 3.1 Implement `start_mock_interview(ctx, metadata)` in `agent.py`


    - Extract `candidate_name`, `job_title`, `resume_summary`, `questions`, `jd_summary` from metadata dict using `.get()` with safe defaults
    - Call `_build_system_prompt` with extracted fields
    - Build `ChatContext` and append the system prompt as a `system` role message
    - Initialize `VoicePipelineAgent` with `silero.VAD.load()`, `deepgram.STT(model="nova-3")`, `openai.LLM(model="gpt-4o-mini")`, `sarvam.TTS(voice="simran")`, and the `chat_ctx`
    - Call `agent.start(ctx.room)`
    - Call `agent.say(...)` with an opening greeting that includes `candidate_name` and `job_title`
    - _Requirements: 2.3, 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2_

  - [x] 3.2 Implement `entrypoint(ctx: JobContext)` in `agent.py`

    - Decorate with `@server.rtc_session(agent_name="practice-interview-agent")`
    - Call `await ctx.connect()`
    - Read `ctx.room.metadata`; if empty/null, log error and return
    - Wrap `json.loads(room_metadata_str)` in try/except `json.JSONDecodeError`; log error and return on failure
    - Call `await start_mock_interview(ctx, metadata)` on success
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2_

- [x] 4. Wire worker bootstrap and verify startup





  - [x] 4.1 Add `cli.run_app` bootstrap to `agent.py`


    - Add `if __name__ == "__main__":` block
    - Instantiate `WorkerOptions` with `entrypoint_fnc=entrypoint`, `api_key=settings.LIVEKIT_API_KEY`, `api_secret=settings.LIVEKIT_API_SECRET`, `ws_url=settings.LIVEKIT_URL`
    - Call `cli.run_app(WorkerOptions(...))`
    - Add all required imports: `json`, `logging`, `livekit.agents` components, `config.settings`
    - _Requirements: 1.4, 6.1, 6.2_

  - [x] 4.2 Create `scripts/verify_phase7.py`


    - Import `_build_system_prompt` from `agent` and run it with a fixture metadata dict
    - Assert the output string contains the fixture candidate name, job title, and all 8 question texts
    - Assert none of the banned buzzwords appear in the output
    - Assert `entrypoint` is an async coroutine function via `asyncio.iscoroutinefunction`
    - _Requirements: 2.4, 3.2, 3.4, 6.1_
