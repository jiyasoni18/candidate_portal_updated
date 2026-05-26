# Frontend Overview: Next.js Candidate Portal UI

## 1. Objective
Build a premium, highly responsive, single-user candidate dashboard using Next.js (App Router), Tailwind CSS, and Lucide React icons. The frontend will communicate directly with our local FastAPI Docker containers to manage file uploads, status polling, and real-time LiveKit audio integration.

## 2. Global UI / UX Design System
- **Theme**: Dark mode by default (slate-900 backgrounds, clean borders, crisp zinc text) to give a high-end, premium engineering feel.
- **Micro-interactions**: Use loading skeletons for asynchronous states and disabled button locks to prevent duplicate submissions or race conditions.

## 3. The 3-Phase Frontend Architecture
- **Phase 1: Dashboard, Upload Form, and Layout Infrastructure**
  - Sets up the core layout, navigation sidebar, historical practice sessions grid, and the multi-part file upload form modal.
- **Phase 2: Live Status Polling & Resume Report Card View**
  - Implements the interval polling client logic to track processing states. Renders the detailed 100-point alignment report, including core strengths, gaps, and the custom interview unlock triggers.
- **Phase 3: LiveKit WebRTC Voice Workspace & Assessment Closer**
  - Mounts the `livekit-client` JS SDK interface, handles microphone/audio device permissions, connects to the WebRTC room, and renders the post-interview performance grading dashboard once the call completes.