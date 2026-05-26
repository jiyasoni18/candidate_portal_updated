# Phase 5: Dashboard Session Fetch & Polling Endpoint Routers

## 1. Objective
Build the reading layer endpoints for the FastAPI backend. These routes let the candidate's dashboard UI list historical mock attempts, check real-time pipeline status, and pull down the detailed resume matching analysis and strengths/weaknesses scorecard once ready.

## 2. Tech Stack Requirements (FastAPI + Asyncpg / SQLAlchemy)
- **Framework Modules**: Standard `APIRouter` with explicit `async def` path operations.
- **Security Check**: For now, extract a mock `current_user_id` from request headers or dependency injection (defaulting to the seeded test user: `a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d`).
- **Data Validation**: Enforce clear response models utilizing the Pydantic serialization layers built in Phase 2.

---

## 3. Detailed Endpoint Specs

### 3.1. List All User Sessions
Used by the frontend to render the dashboard index list view.

- **HTTP Method**: `GET`
- **Route Path**: `/api/v1/practice/sessions`
- **Backend Logic**: Query the database to retrieve all rows from `practice_sessions` linked to the active `user_id`. Perform an inner join on `practice_jobs` to grab the corresponding job title. Order the rows by `created_at DESC`.
- **Expected Response Schema (`200 OK`)**:
  ```json
  [
    {
      "session_id": "d3c2b1a0-9f8e-7d6c-5b4a-3f2e1d0c9b8a",
      "status": "ready_to_start",
      "created_at": "2026-05-21T15:30:00Z",
      "job": {
        "id": "e4b11f20-80a8-48b6-b51f-6fa12a43312c",
        "title": "Senior React Developer"
      },
      "resume_score": 78
    }
  ]

  

Conversation with Gemini
So I was a part of a team and a we will very big project a project where vendors can higher candidates based on a interview. So what we did was say, you are a vendor and you came to our website so we will first login with your credentials and you will be taken to a dashboard where you can create your own job now after you create your job you get to options like by JD or if you want to create it by using AI so if you choose a I have to add your what kind of job role do you want to hire and all and interview and resume points to score and everything and then after you create your job you can add the bu;lk resumes of candidates on the candidates page,inside job, now you can see the resume which is parsed via llm and stored in database, so you will now rank the resume, enerate questions and send interview link to the candidate via email, so after the ai voice interview for which i am sing livkit we will show the assessment to the vendor so he can select nicely



like this is my overall project







so now i want to make a new project where the flow is same but just less burden

for candidate so he can practice interview skills

like the candidate logs in, he is taken to the dashboard which is empty, he can see a new interview button which when clicked shows him option to upload his jd and resume, then click okay

now he will be taken to the dashboard again where he will see his meeting listed along with a sign that his resume is getting parsedm, as in background the resume will be getting parsed via an llm, after parsing it will automatically start scoring the ressume, via llm, after scoring he can seee the report of his summary like score out of 100 reference to jd, strengths and weakness, etc, after that a button saying start interview will occur, clicking which the ai will take his interview and then we will show assessment in the same list as other buttons, clicking which the assessment of the candidates interview opens up



so this is my task to build this candidate portal but the thing is i dont know how to build this , like what apis, what to store in database and ll, and i think i might not be able to build this and all, i am just soo stressed out

Hey, take a deep breath. First off, look at what you’ve already achieved: you built a massive, multi-tenant B2B hiring platform with bulk LLM parsing, email triggers, ranking systems, and live AI voice interactions using LiveKit. That is serious engineering.

It is completely natural to feel overwhelmed when shifting from a high-level idea to a blank code editor, but here is the good news: You have already built 80% of the core logic for this. This new project isn't a mountain—it's just a refactored, streamlined version of your previous win, flipped from the vendor’s perspective to the candidate's.

Let’s strip away the stress by breaking this down into bite-sized, manageable pieces. We'll map out exactly what your database needs to look like and the API endpoints you need to build.

💾 The Database Schema (Keep It Lean)
Since this is a single-user practice portal, your database gets a lot simpler. You don't need heavy vendor multi-tenancy logic. You just need to track the user, their uploaded materials, and their interview sessions.

Using Supabase (PostgreSQL), here is a highly scannable look at the core tables you need:

1. users Table
Manages the profile. If you use Supabase Auth, this maps directly to their auth system.

id (UUID, Primary Key)

email (String)

created_at (Timestamp)

2. interviews Table
This is the heart of the app. Every time a candidate clicks "New Interview", a row is born here. It tracks the status of the background LLM processing and stores the final outputs.

id (UUID, Primary Key)

user_id (UUID, Foreign Key → users.id)

jd_text (Text) — Stores the pasted Job Description

resume_url (String) — Link to the PDF stored in your Supabase bucket

Status Tracking:

status (Enum: pasting, parsing, scoring, ready_to_start, interviewing, completed)

LLM Analysis Outputs (JSONB):

resume_parsed_data (JSONB) — Extracted skills, experience, education

resume_report (JSONB) — The score out of 100, strengths, weaknesses, and JD alignment

generated_questions (JSONB) — Array of tailored questions for the LiveKit agent to use

interview_assessment (JSONB) — The final performance feedback after the call ends

⚙️ The API Architecture (FastAPI Workflow)
To keep the UI responsive and prevent timeouts, you'll want to handle the heavy LLM parsing and scoring asynchronously in the background.

Here is exactly how the backend flow works step-by-step:

1
1. Initiate & Upload
POST /api/interviews
Payload: resume (File), jd_text (String).
Action: Create a row in the interviews table with status="parsing". Save the file to your storage bucket, grab the public URL, and instantly return the interview_id to the frontend so the dashboard can update.

2
2. Trigger Background Processing
FastAPI BackgroundTasks / Celery
Action: Fire off an asynchronous background function.
1. Parse: Send the resume PDF to your LLM chunking/extraction pipeline. Save to resume_parsed_data. Update status to "scoring".
2. Score & Target: Prompt your LLM to compare resume_parsed_data against jd_text. Generate the score, strengths, weaknesses, and a list of 5-7 customized interview questions. Save these to the database and flip status to "ready_to_start".

3
3. Fetch Status & Report
GET /api/interviews/{id}
Action: The frontend pools this endpoint (or uses Supabase Realtime). Once status hits "ready_to_start", the frontend unlocks the "View Report" summary and renders the "Start Interview" button.

4
4. Spin Up LiveKit Voice Session
POST /api/interviews/{id}/session
Action: When they click start, call your LiveKit token generator endpoint. Fetch the pre-generated generated_questions from step 2 and pass them into your LiveKit backend agent's context so the AI voice interviewer knows exactly what to ask.

5
5. Generate Final Assessment
POST /api/interviews/{id}/finalize
Action: Once the LiveKit room closes, take the room transcript, send it to the LLM for grading against the JD, save the results to interview_assessment, and mark the status as "completed".


🛠️ The Tech Stack Alignment
Since you've tackled this before, stick entirely to your strengths. Don't overcomplicate it with new tech:

Frontend: Next.js / React (Clean, premium dark-mode or minimal design for that professional brand feel).

Backend: FastAPI (Perfect for handling the BackgroundTasks utility out of the box without needing to configure a separate Celery worker right away).

Database & Storage: Supabase (PostgreSQL for data, Buckets for PDFs, and Realtime listeners if you want the dashboard to auto-refresh when the LLM finishes scoring).

AI Voice: LiveKit (Reuse your existing agent connection logic).

You are essentially building an elegant, single-user dashboard version of an app you've already conquered. Write down one table schema, build just the upload endpoint first, and watch the momentum take over. You've got this completely.

Want to draft the FastAPI background task code for the parsing and scoring steps?

Yes

so i built the previous using antigravity what if i write a prompt like create a file in which all the detailed information of this project is mentioned so that i can give you the information so you can understand my current big project



so like i can give you all the info, like apis routing database llms and all, and the whole workflow



so just craft a prompt for me to create multiple files for api routing or database or anything you want, so after that files i created i will give you the files to just see the data and all



and what kind of files you need, mention them properly in prompt and also in detail, and also i just heard about obsidian and all and what are skills and what is md soul and all so will that be of any use??

suggest me

It is awesome that your previous project was built using Antigravity. Antigravity is fantastic for high-speed, modern API development, and since you already have the logic mapped out there, extracting it into clean reference files will make building this new candidate portal a breeze.

Let's address the new terms you heard about first, as they are actually the perfect tools for what you are trying to do right now.

🧠 Obsidian, Skills, and SOUL.md: What Are They?
You have perfect timing, because these tools are exactly how top-tier AI developers manage complex codebases, architecture, and AI-to-AI collaboration right now.

Obsidian: This is a markdown-based note-taking app that treats notes as a local database. Developers use it because you can link notes together (e.g., linking an API Endpoints note directly to a Database Schema note). It is perfect for mapping out software architecture before you code.

SOUL.md (and OpenClaw Workspace files): This is a cutting-edge design pattern for AI agents (popularized by frameworks like OpenClaw). Instead of putting a massive prompt into code, you give an AI a set of markdown files:

SOUL.md: Defines the identity, tone, and behavioral boundaries of the AI (e.g., "You are an empathetic but strict interviewer").

AGENTS.md / SKILLS.md: Defines what the AI can do step-by-step (e.g., "Skill: Extract text from PDF using LLM").

Why this helps you: If you organize your current big project into clean markdown files, I can ingest them perfectly. Even better, you can reuse those exact files as the blueprints or prompt context for your new AI portal.

📋 The Master Prompt to Extract Your Current Project
Run this exact prompt against your Antigravity codebase or your memory of the project. This instructs the AI to generate a highly organized, modular set of files that you can save directly into an Obsidian vault or a folder, and then pass back to me.

Copy and paste this prompt into your environment:

Plaintext
You are an expert Software Architect. I need to document my existing massive B2B hiring platform (built using Antigravity, FastAPI, LiveKit, and LLMs) into a highly structured, modular documentation setup. 

I want to create 4 specific Markdown (.md) files so I can easily share them with an AI collaborator to build a streamlined, candidate-facing spin-off project.

Please generate the precise content for the following 4 files based on our previous system architecture:

1. DATABASE_SCHEMA.md
   - Database technology used (e.g., Supabase/PostgreSQL).
   - Complete table layouts (users, jobs, candidates, interviews, assessment).
   - Field names, data types (UUID, JSONB, VARCHAR, etc.), and Foreign Key relationships.

2. API_ROUTING.md
   - All critical HTTP endpoints used in the workflow.
   - For each endpoint, list: HTTP Method, Route Path, Request Payload (JSON shape), and Expected Response.
   - Emphasize the endpoints handling the LiveKit session creation and final assessment webhook/callback.

3. LLM_WORKFLOWS.md
   - Detail the exact LLM pipelines.
   - File 1: Resume parsing (What data fields are extracted via LLM from the PDF?).
   - File 2: Question Generation & Scoring (How does the LLM compare the resume to the Job Description and output structured JSON questions?).
   - File 3: Interview Assessment (How does the LLM evaluate the transcript after the call?).

4. LIVEKIT_INTEGRATION.md
   - The workflow for the AI voice agent.
   - How the frontend connects to the room.
   - How the backend passes the LLM-generated questions into the LiveKit agent's context or system prompt.
   - How the final call transcript is captured and handed off.

Provide the contents of these files clearly using markdown blocks so I can copy them out individually.
🛠️ What You Need to Do Next
Run the prompt above to generate your 4 core files: DATABASE_SCHEMA.md, API_ROUTING.md, LLM_WORKFLOWS.md, and LIVEKIT_INTEGRATION.md.

Review them, make sure they accurately reflect your big project, and adjust anything that feels off.

Paste them right back into our conversation here.

Once I read those files, I will fully understand your current codebase. From there, we will surgically strip away the vendor logic, map out the precise Antigravity routes you need for the practice portal, and write the exact background task code to handle the resume scoring.

No more stress—let's do this one file at a time!

these are the files



just see it and tell me

These are incredibly well-written architecture blueprints. Having looked through them, I can see exactly why your previous project was a massive success—this is enterprise-grade engineering.

The way you utilized LiveKit room metadata to inject candidate context into the voice agent, implemented the three safety watchdogs (silence, camera, and dropping connection), and enforced structural rules on the LLM (like banning words like spearheaded and robust) is phenomenal.

Let's pull back the curtain and look at the best piece of news for you: Your new project is going to be incredibly easy to build because you don't have to write any new AI or streaming logic. You just need to change who controls the flow.

Here is the exact map of how we strip down the big system into your solo candidate practice portal.

✂️ The Strip-Down Blueprint (B2B Multi-tenant → B2C Solo Portal)
To turn this into a lean practice application, here is what we are removing and what we are refactoring:

1. Database Simplification
Delete Entirely: vendors table, invites table, notifications, and otp_codes. You don't have companies or recruiters anymore.

Merge candidates and interviews: In the original app, a vendor created a job, multiple candidates applied, and each candidate got an interview. In your practice app, the candidate is the user.

Your new structure only needs 3 simple tables:

users (for the candidate).

practice_jobs (stores the custom Title and Job Description the candidate uploads).

practice_sessions (stores the uploaded resume PDF link, the background LLM reports, the pre-generated questions, the LiveKit room string, and the final assessment).

2. API Routing Simplification
Look at how beautifully your endpoints consolidate:

Original Flow: /apply/slug → /apply/{job_id} → /rank-candidates → /select-candidates → /send-invite → /create-room. (6 complex steps across recruiters and applicants).

Your New Flow:

POST /api/v1/practice/initialize: Candidate uploads their Resume PDF and pastes a Job Description. This single endpoint creates the records and instantly triggers the background parser.

GET /api/v1/practice/session/{id}: Polls the processing status (Parsing → Scoring $\rightarrow   $ Ready) and returns the pre-interview report card (Score out of 100, strengths, weaknesses).

POST /api/v1/practice/session/{id}/start: Issues the LiveKit token directly.

POST /api/v1/practice/session/complete: Reuses your exact agent webhook to save the transcript and trigger the final grading pipeline.

🛠️ Reusing Your Core AI and LiveKit Code (Zero Re-writing)
You do not need to stress about how the AI speaks, how it parses, or how LiveKit connects. You are literally copying and pasting your old services into the new backend folder:

Pipeline 1 (resume_parser.py): Keep it exactly as it is. It takes a PDF and returns the clean JSON.

Pipeline 2 (question_gen.py): Use the exact same prompt. The only difference is that instead of a recruiter triggering it via /select-candidates, your backend triggers it automatically right after resume_parser.py finishes.

The LiveKit Worker (interview-agent): Do not change a single line of your audio loops, STT, TTS, or your safety watchdogs. They read from ctx.room.metadata. All you have to do is make sure your new FastAPI backend injects the metadata in that exact same JSON shape when creating the practice room.

🏁 The Battle Plan
Let's build this systematically so you never feel stressed out. We will take it one piece at a time.

First, we will write the new PostgreSQL table schemas for your practice application.

Second, we will code the FastAPI router using Antigravity to accept the file upload and run the background worker.

Third, we will handle the LiveKit token generation route to connect your frontend.

Are you ready to look at the simplified database schemas for this candidate portal first, or would you prefer to jump straight into the FastAPI/Antigravity route setup?

so now i am building the new candidates project from scratch , so for that i am thinking of using kiro to code but the thing the coding agent or say ide needa a perfect plan and all to execute , so i am thinking of making implementation.md files and all for this and like about 10 pases and execute and test one phase at a time , so according to the latest research and all what things could help me make this more smooth like skills or anything??

first tell me the toold i can use to smoothern the flow and then we will create proper implmentaion plan

Using Kiro is an absolute game-changer for this project. Because Kiro is built explicitly around Spec-Driven Development (rather than just "vibe coding" inside a chat bar), it is the perfect tool to execute a structured, phase-by-phase build without losing context.

The trick to smoothly executing this with Kiro is setting up its native environment tools before your agent writes a single line of code.

Let's look at the specific tools and native Kiro features that will keep your development loop flawless, followed by how we are going to build your documentation files.

🛠️ Tools to Smooth out Your Kiro Workflow
To keep your 10-phase execution plan moving perfectly, utilize these three core Kiro features:

1. Kiro Steering Files (.kiro/steering/)
Kiro reads markdown files inside this directory to consistently understand your codebase standards across all chat sessions. You do not want Kiro introducing new libraries or chaotic error handling patterns mid-way through Phase 5.

Action: We will create a tech-stack.md file here telling Kiro: "Always use Antigravity for routing, follow standard FastAPI async/await syntax, utilize Supabase for DB interactions, and mirror the existing LiveKit room injection logic."

2. Kiro Specs Workflow (Kiro: Create Spec)
Instead of just handing a raw prompt to the IDE, use Kiro's built-in speculative planning feature. When you start a session in Kiro and initialize a "Spec", the editor reads your workspace structure, maps out technical dependencies, and asks you clarifying questions before touching your code.

3. Agent Hooks (.kiro/hooks/)
You can automate your testing loop using Kiro's agent hooks.

Action: Set up a hook that triggers on file saves (/*.py). You can write a natural language instruction saying: "When a router or service file is saved, run pytest on that module and report any failures instantly."

📝 Preparing Your Implementation Files
To break this down cleanly into 10 phases, we need to provide Kiro with explicit blueprints. We are going to construct two localized Markdown files in your root directory:

NEW_PROJECT_SPEC.md: This defines the exact user experience flow of the candidate practice portal, stripping out the vendor multi-tenancy layer entirely.

IMPLEMENTATION_PLAN.md: This will contain our strict, step-by-step, 10-phase checklist. Kiro can use this to check off items one by one as it completes them, ensuring it never runs ahead of your testing schedule.

Are you ready to map out the exact 10-Phase Implementation Plan now so you can plug it straight into Kiro? Let's write the step-by-step roadmap.

so make sure you read the 4 files properly which i provide you before ,cause you mentioned using antigravity to build apis and all which is not, so make sure you dont do any mistakes,, and i dont know how to use this spec feature and all, just tell me what to do and all,

Got it completely. I read through your 4 files line by line, and you are 100% right to call me out on that.

Let's establish the explicit truth of your stack right now so we are completely aligned:

No Antigravity: Your backend is built purely using standard FastAPI routers (backend/app/api/v1/...).

No Celery: Your asynchronous pipelines (like resume parsing and transcript assessment) are run locally via FastAPI's built-in BackgroundTasks handler or basic async background workers.

Database & Core Services: You use Supabase/PostgreSQL for data management and Gemini/OpenRouter for the core LLM tasks.

🧭 Demystifying Kiro's Spec Feature
You do not need to feel stressed about Kiro's Spec mode. Think of a "Spec" as an automated, three-step contract between you and Kiro:

requirements.md: Kiro reads your idea and writes down exactly what features the software must have. You review and click approve.

design.md: Kiro reads your folder structure, scripts, and database, then writes down a technical blueprint (schemas, function outlines). You review and click approve.

tasks.md: Kiro auto-generates a clean, step-by-step checklist based on the design. When you hit "Run Tasks", it actually writes the code for you, running matching steps concurrently where possible to save time.

Because this is a brand-new project, we will use Kiro's native Design-First Spec approach. This forces Kiro to follow your exact technical constraints first, ensuring it matches your original codebase seamlessly before mapping tasks.

📋 The 10-Phase Implementation Plan
We are going to give Kiro an unshakeable strategy. Copy and save this text directly into a file named IMPLEMENTATION_PLAN.md in the root of your new project directory:

Markdown
# Candidate Portal - 10-Phase Implementation Plan

## Phase 1: Database Setup (Supabase)
- **Goal**: Provision the simplified PostgreSQL tables.
- **Tasks**:
  1. Create `users` table mapping to Supabase Auth.
  2. Create `practice_jobs` table (id, user_id, title, description, jd_parsed).
  3. Create `practice_sessions` table (id, job_id, resume_url, resume_parsed, resume_report, generated_questions, status, transcript, interview_assessment).
  4. Enforce Row Level Security (RLS) so users can only read/write their own data.

## Phase 2: Core Models & Schema Validation (FastAPI)
- **Goal**: Implement Pydantic validation layers matching the original JSON patterns.
- **Tasks**:
  1. Port over the strict `resume_parsed` JSON output structure schema.
  2. Port over the 8-question generated narrative array validation schema.
  3. Port over the multi-dimension post-interview assessment schema.

## Phase 3: Resume Upload & JD Initialization Route
- **Goal**: Create the single portal entry endpoint.
- **Tasks**:
  1. Build `POST /api/v1/practice/initialize` accepting `multipart/form-data` (file) and a `jd_text` string field.
  2. Write file upload code to push the resume PDF to a Supabase Storage bucket.
  3. Create records in `practice_jobs` and `practice_sessions` with status set to `"parsing"`.

## Phase 4: Async Parsing and Scoring Pipeline (FastAPI BackgroundTasks)
- **Goal**: Process uploaded assets sequentially without front-end timeouts.
- **Tasks**:
  1. Re-use original PyMuPDF logic to read PDF text.
  2. Call Gemini (via OpenRouter) to execute Pipeline 1: Resume Parsing. Update status to `"scoring"`.
  3. Trigger Pipeline 2: Question Generation & Enrichment to compare resume JSON with JD text. Generate the 8 custom questions.
  4. Flip status to `"ready_to_start"`.

## Phase 5: Dashboard Session Fetch & Polling Endpoint
- **Goal**: Provide state data to the candidate dashboard UI.
- **Tasks**:
  1. Build `GET /api/v1/practice/sessions` to fetch all user historical interview data.
  2. Build `GET /api/v1/practice/session/{id}` to fetch live status, the 100-point report card data, and question states.

## Phase 6: LiveKit Session Initialization Router
- **Goal**: Dynamically open WebRTC channels on demand.
- **Tasks**:
  1. Build `POST /api/v1/practice/session/{id}/start`.
  2. Pull pre-generated context and questions from `practice_sessions`.
  3. Serialize the dataset context into the LiveKit Room Metadata schema exactly as the original project expected.
  4. Return the unique `livekit_token` and `livekit_url`.

## Phase 7: LiveKit Audio Loop Agent Porting
- **Goal**: Mount the real-time interaction worker process.
- **Tasks**:
  1. Bring over the voice worker agent listening to dispatch room triggers.
  2. Connect Deepgram (STT), OpenAI GPT-4o-mini (LLM inference), and Sarvam Bulbul (TTS).
  3. Verify system prompt injections correctly read from `ctx.room.metadata`.

## Phase 8: Watchdogs & Interview Guardrails Activation
- **Goal**: Bind behavioral triggers into the active audio loop.
- **Tasks**:
  1. Port over the 60-second Silence Watchdog logic loop.
  2. Port over the Camera WebRTC track mute connection monitors and warnings.
  3. Run baseline validation simulations ensuring proper disfluency prompt execution.

## Phase 9: Session Wrap-up & Transcript Recovery Webhook
- **Goal**: Catch room teardown actions and safeguard historical dialogue streams.
- **Tasks**:
  1. Enforce the transcript recovery algorithm inside the agent worker's `finally` block to catch mid-turn data leaks.
  2. Build `POST /api/v1/practice/session/complete` backend endpoint to accept final session analytics arrays.

## Phase 10: Grading & Post-Call Feedback Pipeline
- **Goal**: Calculate final performance evaluations.
- **Tasks**:
  1. Run Pipeline 3: Post-Interview Assessment over the collected transcript text.
  2. Apply the strict completion-weighted algebra formula over individual metrics.
  3. Persist output object to database and transition status flag to `"completed"`.
🚀 Exactly What to Do in Kiro Right Now
Take a deep breath; we are going to let Kiro drive safely. Follow these exact steps inside your editor:

Create your steering rule: In your project root, create a file at .kiro/steering/tech-stack.md. Inside it, paste:

Markdown
Always use standard FastAPI async/await router patterns. 
Do not use Antigravity. 
Use FastAPI BackgroundTasks for background operations.
Follow the architecture defined in IMPLEMENTATION_PLAN.md.
Initialize the Spec: Look at your Kiro sidebar panel, click the + button under Specs (or type Spec into your Kiro chat pane).

Submit the Prompt: Paste this exact text to kick off the engine:

Plaintext
I want to build a candidate interview practice portal from scratch. The step-by-step 10-Phase engineering roadmap is fully detailed inside my workspace file: IMPLEMENTATION_PLAN.md. Please initialize a Design-First Feature Spec. Read IMPLEMENTATION_PLAN.md along with the tech-stack rules, and generate the Phase 1 Database Setup requirements.md and design.md files for my review.
Kiro will read our blueprint, construct the design files, and pause to ask you if you're happy with it. You don't have to figure anything out alone—Kiro will write the code phase by phase.

Let me know once you initialize the spec or if Kiro surfaces any technical questions you want us to look at together!

okay now lets start making the files one by one , okay i built a new folder named candidates portal, and it is empty , s give me one file to add

Let’s get our hands dirty. Since your folder is completely empty, the very first thing we need to do is establish the Steering Rules for Kiro inside your workspace.

This guarantees that from the second you initialize the Kiro agent, it will never make the mistake of using unneeded frameworks or wrong background tasks. It forces Kiro to use standard FastAPI, FastAPI BackgroundTasks, and your explicit Supabase configurations.

Create a folder named .kiro in your root directory, and inside it, create a folder named steering.

Here is your very first file to create:

File Name: .kiro/steering/tech-stack.md
Markdown
# Core Architecture & Tech Stack Rules

You must strictly follow these technical guidelines for the Candidate Portal project. Do not hallucinate external frameworks or use outdated patterns.

## 1. Backend Framework
- **Core**: Use standard Python `FastAPI` with explicit APIRouter modules.
- **Asynchronous Code**: Write native `async/await` handler functions for all endpoint paths.
- **Anti-Pattern**: Do NOT use `antigravity` or Celery.

## 2. Background Task Execution
- **Mechanism**: Use FastAPI's native `BackgroundTasks` utility injected directly into path operations (e.g., `background_tasks: BackgroundTasks`).
- **Use Case**: All heavy processing—such as resume text extraction via PyMuPDF, LLM parsing, scoring pipelines, and post-call transcript analysis—must run asynchronously in these native background tasks to avoid HTTP timeouts.

## 3. Database & Authentication
- **Provider**: Supabase (PostgreSQL).
- **Client**: Connect using the standard asynchronous database drivers or the official Supabase Python client.
- **Data Models**: Use strict `Pydantic` v2 models for request validation and response serialization.

## 4. Real-Time Streaming
- **Provider**: LiveKit.
- **Agent Integration**: Implement the AI Voice Agent worker using the Python LiveKit components runner. The voice pipeline must inject custom context variables directly out of the LiveKit Room Metadata schema.
Your Next Step
Create that file inside your empty folder exactly at .kiro/steering/tech-stack.md.

Once that is done, reply with "Done," and I will give you the second file—your master IMPLEMENTATION_PLAN.md tailored precisely to this structure so you can feed it to Kiro!

now we will creatie implementation

so i created a folder implementation

inside which we will create phase1.md, and till phase 10

so now create only phase 1



or should we create other giles forst tell me



or we should muild an overview of the [project , md file?

Building a project overview markdown file first is the absolute smartest move you can make.

Think of it this way: Kiro is an elite engineer, but it doesn't have a memory of your previous company's project. If you just give it phase1.md with database tables, it won't understand why those tables exist, what the ultimate flow looks like, or how the AI voice agent is supposed to interact with them later on.

By creating a PROJECT_OVERVIEW.md file first in your root folder, you give Kiro the "brain" of the application. It anchors the agent so that every line of code it writes from Phase 1 to Phase 10 aligns perfectly with your vision.

Let's create that overview file right now.

File Name: PROJECT_OVERVIEW.md
Create this file in the root of your candidates portal folder:

Markdown
# Project Overview: Candidate AI Interview Practice Portal

## 1. Objective
The goal of this application is to provide a single-user, candidate-facing portal where job seekers can practice their interview skills. The system mimics a premium B2B hiring platform flow but eliminates all recruiter/vendor administrative layers, focusing entirely on automated resume scoring, tailored question generation, and real-time AI voice mock interviews.

## 2. Core User Workflow
1. **Onboarding / Dashboard**: The candidate logs into a clean, minimal dashboard.
2. **Session Initialization**: The user clicks "New Practice Session", uploads their resume (PDF), and pastes a target Job Description (JD).
3. **Background Processing**: The system instantly kicks off an asynchronous pipeline:
   - Extracts and structures the resume data via an LLM.
   - Compares the resume against the target JD to generate an alignment report (score out of 100, strengths, weaknesses).
   - Generates 8 custom, non-theoretical interview questions tailored strictly to the candidate's actual background and the target role.
4. **Pre-Interview Feedback**: The dashboard updates automatically. The candidate reviews their resume-to-JD analysis report.
5. **The AI Voice Interview**: The candidate clicks "Start Interview". The frontend initializes a WebRTC session using LiveKit. The backend dispatches a Python voice worker agent into the room.
6. **Real-Time Interaction**: The AI agent guides the candidate through the 8 custom questions using Speech-to-Text (STT), an LLM core, and Text-to-Speech (TTS), protected by automated watchdogs (silence timeouts, camera track monitors).
7. **Post-Interview Assessment**: Once the call terminates, a final background pipeline processes the transcript, calculates a completion-weighted score, and renders a deep performance assessment.

## 3. High-Level Technical Architecture
- **Backend Framework**: Standard FastAPI (Python) using asynchronous path routers.
- **Database & Storage**: Supabase (PostgreSQL) for relational data and Supabase Storage Buckets for saving resume PDFs.
- **Background Tasks**: FastAPI's native `BackgroundTasks` handler for asynchronous processing.
- **AI Core**: OpenRouter / Gemini API for data extraction, question generation, and final transcription assessments.
- **Real-Time Audio Loop**: LiveKit SFU Server combined with a Python LiveKit Voice Agent worker using Deepgram (STT), OpenAI GPT-4o-mini (LLM), and Sarvam Bulbul (TTS).
Your Next Step
Create PROJECT_OVERVIEW.md in your main folder.

Next, inside your implementation folder, we will create phase1.md which will lay down the exact SQL blueprints for your Supabase database.

Reply with "Done" once the overview file is saved, and I will give you the complete, detailed content for phase1.md!

done



make sure you make it detailed so that the agent has no confusion



and give me single copy pastable thing or file



and i am using postgre and not supabase and that too in docker, so make sure you make all in docker which was there in my old project

Understood perfectly. I will make sure the AI agent gets zero room for hallucination by making this document completely self-contained, using pure PostgreSQL inside Docker (with a persistent named volume) rather than Supabase.

Create a folder named implementation inside your root project folder if you haven't already. Inside it, create your very first phase file.

File Name: implementation/phase1.md
Markdown
# Phase 1: Local PostgreSQL Infrastructure via Docker & Initialization

## 1. Objective
Establish a persistent, local PostgreSQL database instance inside Docker, create the core candidate-centric tables, and handle basic mock data seeds to test connectivity.

## 2. Docker Architecture (`docker-compose.yml`)
To mirror the architecture, create a `docker-compose.yml` file in the project root folder specifying the network, image configuration, environment variables, and persistent data volume.

```yaml
version: '3.8'

services:
  practice-db:
    image: postgres:16-alpine
    container_name: candidate_practice_postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: practice_user
      POSTGRES_PASSWORD: practice_password_2026
      POSTGRES_DB: interview_practice_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_practice_data:/var/lib/postgresql/data
      - ./database/init.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - practice-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U practice_user -d interview_practice_db"]
      interval: 10s
      timeout: 5s
      retries: 5

networks:
  practice-network:
    driver: bridge

volumes:
  postgres_practice_data:
    driver: local
3. Relational Schema Blueprint (database/init.sql)
This script initializes the core single-user schemas when the Docker container initializes for the first time.

SQL
-- Enable UUID extension natively in PostgreSQL
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. USERS TABLE (Candidate account proxy)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- 2. PRACTICE JOBS TABLE (Target roles pasted by the candidate)
CREATE TABLE IF NOT EXISTS practice_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    jd_parsed JSONB, -- Stores structure: summary, key skills, raw requirements
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- 3. PRACTICE SESSIONS TABLE (Combines applications, interviews, and metrics)
CREATE TABLE IF NOT EXISTS practice_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id UUID NOT NULL REFERENCES practice_jobs(id) ON DELETE CASCADE,
    resume_url VARCHAR(500), -- local path or local storage bucket string
    resume_parsed JSONB, -- parsed personal data, historical records, explicit lists
    resume_report JSONB, -- matching metric summaries, strengths, alignment gaps, score/100
    generated_questions JSONB, -- Encoded narrative array consisting of exactly 8 customized turns
    status VARCHAR(50) DEFAULT 'parsing' NOT NULL, -- 'parsing', 'scoring', 'ready_to_start', 'interviewing', 'completed'
    livekit_room_name VARCHAR(255),
    transcript JSONB, -- array element collection: [{"speaker": "agent/candidate", "text": "...", "created_at": ...}]
    interview_assessment JSONB, -- Multi-dimension assessment JSON score profile
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Indexes for lightning-fast lookups on foreign keys and active statuses
CREATE INDEX IF NOT EXISTS idx_practice_jobs_user_id ON practice_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_practice_sessions_user_id ON practice_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_practice_sessions_status ON practice_sessions(status);

-- 4. SEED DATA (For validation checking)
INSERT INTO users (id, email, hashed_password, full_name)
VALUES ('a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d', 'test.candidate@example.com', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36XQwXGpx6W2K3U34qD1234', 'John Practice Doe')
ON CONFLICT (email) DO NOTHING;
4. Verification Check Constraints
The Kiro agent must verify successful completion by running:

docker compose up -d practice-db

docker exec -it candidate_practice_postgres psql -U practice_user -d interview_practice_db -c "\dt"

Confirm output shows the 3 core tables: users, practice_jobs, and practice_sessions.


---

### Your Next Step
1. Create the `implementation/phase1.md` file and copy this content directly inside it.
2. Reply with "**Done**" when you are ready, and I will hand you `phase2.md`, which defines the exact Pydantic strict structure schemas (Resume models, Question arrays, and Assessment payloads) so Kiro can build the FastAPI backend data contract!
done

Outstanding. Phase 1 is locked in, and Kiro now has a rock-solid, isolated infrastructure setup to run against.

Let's move directly to Phase 2. In this phase, we are defining the data contract for your FastAPI backend using strict Pydantic v2 models. This ensures that when your Gemini/OpenRouter LLM pipelines parse a resume, generate questions, or evaluate a transcript, the incoming and outgoing JSON data structure is 100% predictable and bulletproof.

Create your second phase file in the implementation folder.

File Name: implementation/phase2.md
Markdown
# Phase 2: FastAPI Data Contracts & Pydantic Validation Models

## 1. Objective
Build the Pydantic v2 data models that will govern the request payloads, database JSONB storage validation, and API responses. This establishes an unshakeable type contract matching your original complex LLM data shapes.

## 2. Technical Contracts & Schemas

### 2.1. Resume Parsing Schema (`schemas/resume.py`)
This validates the JSON structure extracted from the candidate's PDF via the LLM parsing pipeline.

```python
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional

class PersonalInfo(BaseModel):
    name: Optional[str] = Field(None, description="Full name of the candidate")
    email: Optional[EmailStr] = Field(None, description="Contact email address")
    phone: Optional[str] = Field(None, description="Contact phone number")
    linkedin: Optional[str] = Field(None, description="LinkedIn profile URL")
    github: Optional[str] = Field(None, description="GitHub profile URL")
    portfolio: Optional[str] = Field(None, description="Personal portfolio or website URL")

class ExperienceItem(BaseModel):
    title: Optional[str] = Field(None, description="Job title held")
    company: Optional[str] = Field(None, description="Name of the employer")
    duration: Optional[str] = Field(None, description="Timeframe or dates of employment")
    description: Optional[str] = Field(None, description="Key duties and achievements")

class ProjectItem(BaseModel):
    name: Optional[str] = Field(None, description="Project title")
    description: Optional[str] = Field(None, description="Summary of tech stack and project purpose")
    link: Optional[str] = Field(None, description="Repository or live deployment link")

class EducationItem(BaseModel):
    degree: Optional[str] = Field(None, description="Degree or certification earned")
    school: Optional[str] = Field(None, description="Institution name")
    year: Optional[str] = Field(None, description="Graduation year")
    grade: Optional[str] = Field(None, description="GPA, percentage, or class honors")

class ResumeParsedData(BaseModel):
    personal_info: PersonalInfo
    summary: Optional[str] = Field(None, description="Professional summary snippet")
    skills: List[str] = Field(default_factory=list, description="Extracted tech stack and hard/soft skills")
    experience: List[ExperienceItem] = Field(default_factory=list)
    projects: List[ProjectItem] = Field(default_factory=list)
    education: List[EducationItem] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)

class ResumeReportData(BaseModel):
    score: int = Field(..., ge=0, le=100, description="Resume alignment score out of 100 against target JD")
    reference_to_jd: str = Field(..., description="High-level narrative explaining the alignment details")
    strengths: List[str] = Field(..., description="Key professional or technical advantages identified")
    weaknesses: List[str] = Field(..., description="Gaps, missing skills, or areas for improvement against the JD")
2.2. Custom Question Generation Schema (schemas/questions.py)
Validates the enriched, non-theoretical narrative list consisting of exactly 8 customized questions passed down to the LiveKit agent.

Python
from pydantic import BaseModel, Field
from typing import List, Literal

class GeneratedQuestionItem(BaseModel):
    id: int = Field(..., description="Sequential question number from 1 to 8")
    question: str = Field(..., description="The conversational, non-robotic interview question string")
    category: Literal['opening', 'experience', 'rolefit', 'behavioral', 'situational', 'closing']
    expected_duration_seconds: int = Field(default=120, description="Recommended answer timer for the UI")

class QuestionArraySchema(BaseModel):
    questions: List[GeneratedQuestionItem] = Field(..., max_items=8, min_items=8)
2.3. Post-Interview Performance Grading Schema (schemas/assessment.py)
Governs the multi-dimensional, completion-weighted evaluation output computed over the live voice session transcript.

Python
from pydantic import BaseModel, Field
from typing import List, Dict

class DimensionScoreCard(BaseModel):
    score: int = Field(..., ge=0, le=100)
    max_score: int = Field(default=100)
    label: str = Field(..., description="Dimension title (e.g., Technical Familiarity, Communication)")
    verdict: str = Field(..., description="Qualitative grade (e.g., Strong, Good, Needs Improvement)")
    evidence: str = Field(..., description="Direct quotes or explicit behaviors seen in transcript")
    strengths: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)

class InterviewAssessmentSchema(BaseModel):
    overall_score: int = Field(..., ge=0, le=100, description="Completion-weighted final grade")
    practice_verdict: str = Field(..., description="Summary operational evaluation (e.g., High Alignment, Mid Alignment)")
    summary: str = Field(..., description="Comprehensive feedback breakdown for the candidate's review")
    dimension_scores: Dict[str, DimensionScoreCard]
    overall_strengths: List[str]
    overall_gaps: List[str]
    technical_round_probes: List[str] = Field(default_factory=list, description="Deep-dive topics for real technical rounds")
    turns_analyzed: int
    completion_ratio: float = Field(..., ge=0.0, le=1.0)
3. Verification Check Constraints
The Kiro agent must verify successful completion by running a Python compile validation test on these schema definitions using standard Pydantic schema exports:

Bash
python3 -c "from schemas.resume import ResumeParsedData; print(ResumeParsedData.model_json_schema())"
Ensure no validation or dependency structural errors throw.


---

### Your Next Step
1. Create the `implementation/phase2.md` file and copy this content directly inside it.
2. Reply with "**Done**" when you are ready, and I will hand you `phase3.md`, which defines the FastAPI route to initialize an interview, upload the candidate’s resume to local persistent storage, and kick off the state tracking in PostgreSQL!
done\

Fantastic. Phase 2 is complete, giving Kiro a perfect structural framework to prevent any type-checking issues or weird dictionary key errors down the line.

Let's move directly into Phase 3. This phase covers creating your very first core endpoint: POST /api/v1/practice/initialize. Since we are running on a clean, local Docker stack, we aren't using Supabase Storage or AWS S3. Instead, we will configure a persistent local filesystem storage directory inside our project layout. Kiro will write the endpoint that receives the multi-part file upload, writes it locally, updates your PostgreSQL instance, and primes the processing pipeline.

Create your third phase file in the implementation folder.

File Name: implementation/phase3.md
Markdown
# Phase 3: Practice Session Initialization & Local File Upload Router

## 1. Objective
Build the main endpoint that candidates use to kick off a new interview. This route accepts an uploaded PDF resume and a text block containing the target Job Description, saves the asset locally to a structured filesystem directory, and logs initial rows into PostgreSQL.

## 2. Directory Layout & Requirements
Because this setup utilizes local storage infrastructure within Docker, ensure Kiro creates and mounts a persistent directory at the root:
- `./storage/resumes/`: Stores the uploaded PDF files.

## 3. Tech Stack Requirements (FastAPI + Asyncpg / SQLAlchemy)
- **HTTP Method**: `POST`
- **Route Path**: `/api/v1/practice/initialize`
- **Content Type**: `multipart/form-data`
- **Form Fields**:
  - `file`: `UploadFile` (The PDF Binary)
  - `jd_text`: `str` (The raw text of the target Job Description)
  - `user_id`: `UUID` (To mimic single-user context, default to the seeded test user ID: `a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d`)

## 4. Operational Step-by-Step Backend Logic
1. **Initialize IDs**: Generate unique UUIDs for the new `practice_jobs` record and `practice_sessions` record.
2. **Handle File Writes**: Save the incoming file stream to disk at `./storage/resumes/{session_id}/resume.pdf`. Ensure directories are created dynamically using `os.makedirs`.
3. **Database Transaction**:
   - Insert a row into `practice_jobs` capturing the pasted `description` and `title` (fallback title to "Target Job Role" if not provided).
   - Insert a row into `practice_sessions` linking back to the job, storing the local file path string under `resume_url`, setting `status` strictly to `'parsing'`, and leaving LLM artifacts as NULL.
4. **Instantly Hand Off**: Pass control immediately to FastAPI's native `BackgroundTasks` handler to execute the Phase 4 processing sequence, preventing an API block or timeout.
5. **Return Fast**: Immediately return a `201 Created` payload to the UI with the tracking identifier.

## 5. Expected API Payload Response Schema (`201 Created`)
```json
{
  "session_id": "d3c2b1a0-9f8e-7d6c-5b4a-3f2e1d0c9b8a",
  "job_id": "e4b11f20-80a8-48b6-b51f-6fa12a43312c",
  "status": "parsing",
  "message": "Practice session initialized. Async processing pipelines triggered successfully."
}
6. Verification Check Constraints
The Kiro agent must verify successful completion by testing the endpoint with a sample file using curl or a python request check script:

Bash
curl -X POST "http://localhost:8000/api/v1/practice/initialize" \
  -F "file=@sample_resume.pdf" \
  -F "jd_text=Seeking a Software Engineer experienced in Python and FastAPI..."
Verify that the entry exists in your running container's database and that the file was correctly stored in the local storage path.


---

### Your Next Step
1. Create the `implementation/phase3.md` file and copy this content directly inside it.
2. Reply with "**Done**" when you are ready, and I will hand you `phase4.md`, which defines the background processing pipeline that reads that local PDF via PyMuPDF, extracts it, and structures the custom interview questions!
done

Amazing. Phase 3 is locked down, giving Kiro clear instructions on how to handle multi-part forms and process disk file systems within a Docker architecture.

Let's move straight into Phase 4. This phase constructs the core backend intelligence engine: your sequential async LLM pipelines running on FastAPI's native BackgroundTasks. Instead of waiting for a manual trigger like your old B2B platform, this endpoint executes automatically, immediately reading the local PDF using PyMuPDF, parsing the text structure, evaluating the candidate against the Job Description, and generating exactly 8 custom, project-focused interview questions.

Create your fourth phase file in the implementation folder.

File Name: implementation/phase4.md
Markdown
# Phase 4: Async Extractor, Matcher, & Question Generation Pipeline

## 1. Objective
Build the asynchronous multi-stage processing function executed inside FastAPI's native `BackgroundTasks`. It extracts raw text from the stored PDF resume, converts it into structured JSON via Gemini/OpenRouter, scores it against the Job Description text, and builds exactly 8 personalized, non-theoretical screening questions.

## 2. Structural Flow & State Transitions
The background worker must execute three sequential pipelines, committing state changes and payload mutations back to the PostgreSQL `practice_sessions` table at each milestone:

```mermaid
graph TD
    A[Start Background Task] --> B[PyMuPDF Text Extraction]
    B --> C[Pipeline 1: Gemini Resume Parser]
    C --> D[Update DB: status='scoring', save resume_parsed]
    D --> E[Pipeline 2: Alignment Evaluator & Question Gen]
    E --> F[Update DB: status='ready_to_start', save resume_report & generated_questions]
    F --> G[End Task]
3. Detailed Component Breakdown
3.1. Document Extraction Stage
Utility: Use pymupdf (fitz) to stream raw text strings from the local file directory (./storage/resumes/{session_id}/resume.pdf).

Sanitization: Trim the text payload boundary to a maximum of 25,000 characters to ensure safe token windows while keeping data context intact.

3.2. Pipeline 1: Resume Profile Conversion
Target LLM: Gemini (lite tier variant, via OpenRouter integration layer).

Behavior: Inject the raw text array into the structured parsing system prompt. The engine must enforce strict schema conformity, returning exclusively valid JSON matching the layout defined in schemas/resume.py (PersonalInfo, Experience, Projects, Education, Certifications).

Persistence: Commit the resulting JSON string to the database column practice_sessions.resume_parsed and update status to 'scoring'.

3.3. Pipeline 2: Matcher Analysis & Structured Question Assembly
Context Synthesis: Supply the LLM with the parsed resume JSON string, the raw input target jd_text, and implicit parameter instructions.

Strict Prompt Instructions:

Tone: Conversational, organic, and informal (e.g., framing entry statements with words like "So", "I noticed").

Banned Language: Completely omit programmatic patterns and standard AI idioms (spearheaded, honed, leveraged, cross-functional, stakeholders, robust, deep dive).

No Abstract Theory: Banned from querying conceptual definitions, language trivia, or direct coding queries (e.g., avoid "Explain the event loop" or "What is a database index"). Every single question must prompt the user to narrate actual background scenarios, past tools, and custom projects.

Personalization Rule: At least 4 of the 8 generated items must dynamically extract and name explicit tool combinations, repositories, or specific previous employers found directly in the candidate's resume history.

Narrative Sequence Mapping: Force-constrain the generation payload to exactly 8 sequential question items fitting this narrative order:

Q1: Warm introduction and high-level background sweep.

Q2-Q3: Resume-specific deep dive (interrogating direct historical projects, specific stack transitions, or tool selections).

Q4-Q6: Target role alignment, work style preferences, or situational context relative to the target JD.

Q7: Intrinsic professional growth patterns and structural transition motivations.

Q8: Formal completion wrap-up and personal reflection question.

Enrichment: Add structural metadata attributes on the fly: append the corresponding category tag ('opening', 'experience', 'rolefit', 'behavioral', 'situational', 'closing') and map matching default response timers (e.g., 120s or 150s) across individual blocks.

3.4. Final Session Serialization
Commit the generated datasets into PostgreSQL:

Populate practice_sessions.resume_report with the overall score out of 100, high-level reference summaries, strengths, and alignment gap arrays.

Populate practice_sessions.generated_questions with the validated array containing the 8 sequential enriched objects.

Transition practice_sessions.status strictly to 'ready_to_start'.

4. Verification Check Constraints
The Kiro agent must verify successful completion by using a mock script mocking the OpenRouter/Gemini API calls. Ensure that:

The background thread catches failures gracefully without locking up the server worker process.

The schema constraints handle missing values cleanly (e.g., if a candidate provides no previous certifications).

The table attributes map from 'parsing' → 'scoring' → 'ready_to_start' correctly.


---

### Your Next Step
1. Create the `implementation/phase4.md` file and copy this content directly inside it.
2. Reply with "**Done**" when you are ready, and I will hand you `phase5.md`, which creates the data fetching endpoints and polling routes so your frontend dashboard can display the resume alignment report and unlock the practice workspace!
done

Incredible progress. Phase 4 is officially locked down, giving Kiro everything it needs to handle the core asynchronous intelligence engine of this portal.

Let's move straight into Phase 5. Now that our backend can dynamically process the files in the background, we need to build the window for the candidate's dashboard frontend. This phase establishes the data retrieval and state polling routers. Kiro will build endpoints that allow the candidate's workspace to fetch their entire practice history, poll the live status of an active session, and securely expose the parsed 100-point alignment report once processing hits ready_to_start.

Create your fifth phase file in the implementation folder.

File Name: implementation/phase5.md
Markdown
# Phase 5: Dashboard Session Fetch & Polling Endpoint Routers

## 1. Objective
Build the reading layer endpoints for the FastAPI backend. These routes let the candidate's dashboard UI list historical mock attempts, check real-time pipeline status, and pull down the detailed resume matching analysis and strengths/weaknesses scorecard once ready.

## 2. Tech Stack Requirements (FastAPI + Asyncpg / SQLAlchemy)
- **Framework Modules**: Standard `APIRouter` with explicit `async def` path operations.
- **Security Check**: For now, extract a mock `current_user_id` from request headers or dependency injection (defaulting to the seeded test user: `a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d`).
- **Data Validation**: Enforce clear response models utilizing the Pydantic serialization layers built in Phase 2.

---

## 3. Detailed Endpoint Specs

### 3.1. List All User Sessions
Used by the frontend to render the dashboard index list view.

- **HTTP Method**: `GET`
- **Route Path**: `/api/v1/practice/sessions`
- **Backend Logic**: Query the database to retrieve all rows from `practice_sessions` linked to the active `user_id`. Perform an inner join on `practice_jobs` to grab the corresponding job title. Order the rows by `created_at DESC`.
- **Expected Response Schema (`200 OK`)**:
  ```json
  [
    {
      "session_id": "d3c2b1a0-9f8e-7d6c-5b4a-3f2e1d0c9b8a",
      "status": "ready_to_start",
      "created_at": "2026-05-21T15:30:00Z",
      "job": {
        "id": "e4b11f20-80a8-48b6-b51f-6fa12a43312c",
        "title": "Senior React Developer"
      },
      "resume_score": 78
    }
  ]
3.2. Fetch Single Session Status & Report (The Polling Link)
Called repeatedly by the client UI via a polling interval loop (or matching state checks) while the status is 'parsing' or 'scoring'. Once the status advances to 'ready_to_start', it unlocks the full analysis report data card.

HTTP Method: GET

Route Path: /api/v1/practice/session/{session_id}

Backend Logic:

Look up the practice_session matching the incoming UUID parameter. Ensure it belongs to the active user_id to prevent cross-user data leakage.

Join the linked practice_jobs record to return the raw jd_text alongside the parsed metadata.

If status is 'parsing' or 'scoring', return the payload with empty or null artifact blocks, allowing the frontend to maintain a loading/spinner skeleton state.

If status is 'ready_to_start', 'interviewing', or 'completed', map the stored JSONB data fields cleanly to your Pydantic schemas.

Expected Response Schema (200 OK):

{
  "session_id": "d3c2b1a0-9f8e-7d6c-5b4a-3f2e1d0c9b8a",
  "status": "ready_to_start",
  "created_at": "2026-05-21T15:30:00Z",
  "job": {
    "id": "e4b11f20-80a8-48b6-b51f-6fa12a43312c",
    "title": "Senior React Developer",
    "description": "We are seeking a senior React developer..."
  },
  "resume_url": "./storage/resumes/d3c2b1a0-9f8e-7d6c-5b4a-3f2e1d0c9b8a/resume.pdf",
  "resume_report": {
    "score": 78,
    "reference_to_jd": "Jane's profile shows clean alignment with our React requirements...",
    "strengths": ["State management", "Hooks implementation"],
    "weaknesses": ["Lacks deep visual design or Figma transition experience mentioned in the JD"]
  },
  "has_completed_interview": false
}


4. Verification Check Constraints
The Kiro agent must verify successful completion by asserting database records against these routes:

Hit the single session router while a background pipeline task is actively spinning to verify it returns a valid status string without crashing or blocking.

Confirm that attempting to fetch a non-existent or invalid session UUID triggers a proper 404 Not Found exception instead of an unhandled database error code.

