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