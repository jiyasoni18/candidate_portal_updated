# Core Architecture & Tech Stack Rules

You must strictly follow these technical guidelines for the Candidate Portal project. Do not hallucinate external frameworks or use outdated patterns.

## 1. Backend Framework
- **Core**: Use standard Python `FastAPI` with explicit APIRouter modules.
- **Asynchronous Code**: Write native `async/await` handler functions for all endpoint paths.


## 2. Background Task Execution
- **Mechanism**: Use FastAPI's native `BackgroundTasks` utility injected directly into path operations (e.g., `background_tasks: BackgroundTasks`).
- **Use Case**: All heavy processing—such as resume text extraction via PyMuPDF, LLM parsing, scoring pipelines, and post-call transcript analysis—must run asynchronously in these native background tasks to avoid HTTP timeouts.

## 3. Database & Authentication
- **Provider**: PostgreSQL
- **Client**: Connect using the standard asynchronous database drivers or the official Supabase Python client.
- **Data Models**: Use strict `Pydantic` v2 models for request validation and response serialization.

## 4. Real-Time Streaming
- **Provider**: LiveKit.
- **Agent Integration**: Implement the AI Voice Agent worker using the Python LiveKit components runner. The voice pipeline must inject custom context variables directly out of the LiveKit Room Metadata schema.

## 5. Python Environment Rule
- Always use the local virtual environment located at `./the .venv/` folder for executing scripts, running tests, or installing python dependencies.
- Do NOT install pip packages globally.

## 6. Frontend Framework & Client Integration
- **Framework**: Use standard Next.js (App Router) with explicit client components (`"use client"`) where state handling or WebRTC bindings are mandatory.
- **Styling**: Enforce a unified, premium dark-mode design system using Tailwind CSS (`bg-slate-900`, `text-zinc-100`).
- **WebRTC Client**: Connect to rooms natively using `livekit-client` and `@livekit/components-react`.
- **State Management**: Use native browser `fetch` for API interaction and implement clear client-side `setInterval` polling loops for background tracking states. Clear all intervals explicitly on component unmount.
## 7. 
LiveKit Agents v1 SDK Rules
- The installed SDK is `livekit-agents==1.5.12` (v1.x). Do NOT use v0.x APIs.
- `JobContext` does NOT have `wait_for_disconnect()`. Use `await session.wait_for_inactive()` instead.
- `end_reason` in the session complete webhook MUST be one of: `"normal"`, `"silence_timeout"`, `"disciplinary"`, `"candidate_leave"`. Never use `"error"`.
- Agent dispatch MUST use `lk.agent_dispatch.create_dispatch(CreateAgentDispatchRequest(...))` — rooms do not auto-dispatch agents.
- Do NOT modify `agent.py` to use `ctx.wait_for_disconnect()` — this method does not exist in v1.
