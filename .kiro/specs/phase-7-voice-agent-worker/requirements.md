# Requirements Document

## Introduction

Phase 7 introduces the LiveKit Python Voice Agent Worker — a standalone process (`agent.py`) that runs alongside the FastAPI server. The worker registers with the local LiveKit server, listens for incoming room join events, parses the structured interview context from the room metadata (injected in Phase 6), assembles a dynamic system prompt for the AI interviewer persona "Aria", and drives a full real-time voice pipeline using Deepgram STT, OpenAI GPT-4o-mini LLM, and Sarvam TTS. This is the core real-time interview experience layer of the Candidate Practice Portal.

## Glossary

- **Voice Agent Worker**: The standalone Python process (`agent.py`) that connects to LiveKit and drives the AI voice interview session.
- **LiveKit**: The WebRTC SFU (Selective Forwarding Unit) server that manages real-time audio/video rooms.
- **JobContext**: The LiveKit Agents SDK object passed to the entrypoint function, providing access to the room, metadata, and connection utilities.
- **RoomMetadata**: A JSON string injected into the LiveKit room during Phase 6 provisioning, containing the full interview blueprint (candidate profile, questions, resume summary).
- **RoomMetadataPayload**: The Pydantic model defined in `schemas/livekit.py` that represents the deserialized room metadata structure.
- **VoicePipelineAgent**: The LiveKit Agents SDK class that orchestrates the STT → LLM → TTS pipeline for a real-time voice session.
- **ChatContext**: The LiveKit Agents SDK object that holds the LLM conversation history, including the system prompt.
- **STT**: Speech-to-Text — converts candidate audio to text. Provider: Deepgram (`nova-3` model).
- **LLM**: Large Language Model — generates the AI interviewer's responses. Provider: OpenAI (`gpt-4o-mini`).
- **TTS**: Text-to-Speech — converts the AI's text responses to audio. Provider: Sarvam (`simran` voice).
- **VAD**: Voice Activity Detection — detects when the candidate starts and stops speaking.
- **Aria**: The AI interviewer persona name used in the system prompt.
- **System Prompt**: The instruction block injected into the LLM ChatContext that defines Aria's role, the candidate profile, and the 8-question interview roadmap.
- **WorkerOptions**: The LiveKit Agents SDK configuration object used to register the worker with the LiveKit server.
- **entrypoint**: The async function decorated with `@server.rtc_session` that is invoked for each new room join event.
- **dev mode**: The `--dev` flag passed to `agent.py start` that runs the worker in local development mode against the Docker LiveKit container.

---

## Requirements

### Requirement 1

**User Story:** As a candidate, I want the AI voice agent to automatically join my practice room when I start the interview, so that the session begins without any manual agent setup.

#### Acceptance Criteria

1. WHEN a candidate's LiveKit room is provisioned and the worker process is running, THE Voice Agent Worker SHALL connect to the room by calling `ctx.connect()` within the entrypoint function.
2. WHEN the entrypoint function is invoked, THE Voice Agent Worker SHALL read the `ctx.room.metadata` string to obtain the interview blueprint.
3. IF `ctx.room.metadata` is an empty string or null, THEN THE Voice Agent Worker SHALL log an error message and terminate the session without raising an unhandled exception.
4. THE Voice Agent Worker SHALL register with the LiveKit server using a `WorkerOptions` configuration that specifies the `LIVEKIT_API_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET` values sourced from environment variables.

---

### Requirement 2

**User Story:** As a candidate, I want the AI agent to know my name, target role, and background before the interview starts, so that the questions feel personalized to my profile.

#### Acceptance Criteria

1. WHEN the entrypoint function parses the room metadata, THE Voice Agent Worker SHALL deserialize the JSON string into a `RoomMetadataPayload`-compatible structure containing `candidate_name`, `job_title`, `resume_summary`, and `questions`.
2. IF the room metadata JSON is malformed or missing required fields, THEN THE Voice Agent Worker SHALL log a structured error and terminate the session gracefully without crashing the worker process.
3. WHEN the metadata is successfully parsed, THE Voice Agent Worker SHALL pass the extracted fields to the `start_mock_interview` function to assemble the system prompt.
4. THE Voice Agent Worker SHALL construct a system prompt that includes the candidate's name, target job title, a resume background summary, and the full ordered list of 8 interview questions extracted from the metadata.

---

### Requirement 3

**User Story:** As a candidate, I want the AI interviewer to follow a structured 8-question script during the session, so that the practice covers all relevant interview dimensions.

#### Acceptance Criteria

1. THE Voice Agent Worker SHALL inject the system prompt into a `ChatContext` instance as the first message with role `system` before starting the voice pipeline.
2. WHEN the system prompt is assembled, THE Voice Agent Worker SHALL include all 8 questions from the `questions` array in the metadata, formatted as a numbered roadmap in the prompt body.
3. THE Voice Agent Worker SHALL instruct the LLM via the system prompt to deliver questions in sequential order and to wait for the candidate's response before proceeding to the next question.
4. THE Voice Agent Worker SHALL instruct the LLM via the system prompt to avoid corporate AI buzzwords including "spearheaded", "honed", "leveraged", "cross-functional", "robust", and "deep dive".

---

### Requirement 4

**User Story:** As a candidate, I want the voice pipeline to use high-quality speech recognition and natural-sounding speech synthesis, so that the interview feels realistic.

#### Acceptance Criteria

1. THE Voice Agent Worker SHALL initialize the STT component using `deepgram.STT` with the `nova-3` model.
2. THE Voice Agent Worker SHALL initialize the LLM component using `openai.LLM` with the `gpt-4o-mini` model.
3. THE Voice Agent Worker SHALL initialize the TTS component using `sarvam.TTS` with the `simran` voice configuration.
4. THE Voice Agent Worker SHALL initialize a `VoicePipelineAgent` instance that wires the STT, LLM, TTS, and VAD components together into a single audio processing pipeline.
5. WHEN the `VoicePipelineAgent` is initialized, THE Voice Agent Worker SHALL call `agent.start(ctx.room)` to attach the pipeline to the active LiveKit room.

---

### Requirement 5

**User Story:** As a candidate, I want the AI interviewer to greet me immediately when I join the room, so that the session starts naturally without awkward silence.

#### Acceptance Criteria

1. WHEN `agent.start(ctx.room)` is called, THE Voice Agent Worker SHALL trigger an initial greeting speech output to the room immediately after the pipeline is attached.
2. THE Voice Agent Worker SHALL generate the opening greeting by invoking `agent.say(...)` or the equivalent SDK method with a contextually appropriate welcome message that addresses the candidate by name.
3. WHILE the voice pipeline is active, THE Voice Agent Worker SHALL maintain the audio stream connection until the room is closed or the candidate disconnects.

---

### Requirement 6

**User Story:** As a developer, I want the agent worker to start cleanly in dev mode against the local LiveKit Docker container, so that I can verify the integration without a production environment.

#### Acceptance Criteria

1. WHEN the command `python agent.py start --dev` is executed using the `.venv` Python interpreter, THE Voice Agent Worker SHALL establish a connection to the LiveKit server at the URL specified in the `LIVEKIT_URL` environment variable without throwing a connection handshake exception.
2. THE Voice Agent Worker SHALL source all required credentials (`LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `LIVEKIT_URL`, `OPENAI_API_KEY`, `DEEPGRAM_API_KEY`) from environment variables, with no hardcoded credential values in the source code.
3. IF a required environment variable is missing at startup, THEN THE Voice Agent Worker SHALL raise a descriptive configuration error before attempting to connect to any external service.
