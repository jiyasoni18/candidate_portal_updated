# Phase 7: LiveKit Python Voice Agent Worker Loop Porting

## 1. Objective
Establish the real-time background voice worker process using the Python LiveKit Agents SDK. The agent registers to your local LiveKit server, listens for incoming candidate practice room join events, parses the structured context payload directly out of the room metadata, and instantiates the multi-plugin voice stream.

## 2. Infrastructure & Real-Time Pipeline Setup
Ensure Kiro structures the agent entry point using standard LiveKit plugin wrappers:
- **Speech-to-Text (STT)**: `deepgram.STT(model="nova-3")`
- **Language Model (LLM)**: `openai.LLM(model="gpt-4o-mini")`
- **Text-to-Speech (TTS)**: `sarvam.TTS(voice="simran")` (or matching Indo-English bulbul configuration keys)

---

## 3. Operational Step-by-Step Agent Logic

### 3.1. Server Session Registration (`agent.py`)
Use the native `@server.rtc_session` decorator to claim incoming runtime context handles.

```python
from livekit.agents import JobContext, WorkerOptions, cli, server
import json

@server.rtc_session(agent_name="practice-interview-agent")
async def entrypoint(ctx: JobContext):
    # 1. Establish structural connection to the WebRTC room
    await ctx.connect()
    
    # 2. Extract and decode the injected room blueprint context
    room_metadata_str = ctx.room.metadata
    if not room_metadata_str:
        print("Error: Missing critical room context metadata array. Terminating session.")
        return
        
    metadata = json.loads(room_metadata_str)
    
    # 3. Hand control off to the core prompt assembly module
    await start_mock_interview(ctx, metadata)

3.2. Dynamic System Prompt Construction
The function start_mock_interview must extract the variables and assemble a highly targeted System Instructions markdown block to feed directly into the LLM chat history context (ChatContext):

# Role and Core Directive
You are Aria, an empathetic, encouraging, yet professional AI interviewer. This is a casual practice interview context designed to help the candidate practice their communication style.

# Candidate Profile
- Name: {candidate_name}
- Target Role: {job_title}
- Background Summary: {resume_summary}

# Fixed Interview Roadmap (Your Questionnaire Guide)
You must guide the conversation through these 8 custom questions generated for this candidate. Do not improvise new primary questions. Stick to this narrative script order:
1. {Q1}
2. {Q2}
3. {Q3}
4. {Q4}
5. {Q5}
6. {Q6}
7. {Q7}
8. {Q8}

# Interaction Constraints
- **Conversation Management**: Deliver your opening greeting question immediately. Wait patiently for the user to respond before proceeding to the next sequential question number.
- **Follow-up Rules**: You are permitted to ask concise, conversational follow-up questions to dig deeper into their project details or past tech stack layers if their initial answer is too brief or deflecting, but always pivot smoothly back to the core roadmap sequence.
- **Word Constraints**: Do NOT use corporate AI buzzwords (spearheaded, honed, leveraged, cross-functional, robust, deep dive). Keep your voice natural, supportive, and distinctly human.

3.3. Multi-Modal Audio Streaming Connection
Initialize the VoicePipelineAgent (or matching LiveKit agent orchestration bundle) linking the configured STT, LLM, TTS, and VAD (Voice Activity Detection) instances.

Call agent.start(ctx.room) to bridge the real-time audio pipeline.

Trigger the initial greeting text speech output immediately to start the session conversation.

4. Verification Check Constraints
The Kiro agent must verify successful completion by starting the worker script in local testing mode:

python3 agent.py start --dev

Ensure that the script establishes contact with your running LiveKit Docker container and registers its availability without throwing connection handshake exceptions.