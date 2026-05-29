# Candidate Portal

A full-stack application featuring an AI-driven mock interview pipeline, resume analysis, and a Next.js dashboard.

## Project Structure

The repository is now divided into three core microservices:

- `frontend/`: The Next.js web application dashboard and interview studio UI.
- `backend/`: The FastAPI core API, handling authentication, database operations, and resume ATS scoring.
- `agent/`: The Python LiveKit Voice Agent worker that drives the real-time AI mock interview.

## How to Start the Project

Because the project is split into separate microservices, you will need to run them concurrently. 

### 1. Start the Database & Backend API (Docker)
We use Docker to automatically orchestrate the PostgreSQL database and the FastAPI backend. 
Open a terminal in the root of the project and run:
```bash
docker compose up --build -d
```
*(Note: This runs in the background. The Backend API will be available at `http://localhost:8000`)*

### 2. Start the Frontend Application
Open a new terminal, navigate to the frontend folder, and start the Next.js development server:
```bash
cd frontend
npm run dev
```
*(The UI will be available at `http://localhost:3000`)*

### 3. Start the LiveKit Voice Agent
Open a third terminal, make sure your Python virtual environment is activated, and start the voice agent worker:
```bash
cd agent
python agent.py start
```
*(This connects to your LiveKit cloud project and listens for incoming interview sessions)*
