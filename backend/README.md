# VidyāMitra Backend (FastAPI)

This folder contains the backend API for the VidyāMitra application. It is built with FastAPI and exposes endpoints for authentication, resume parsing, learning plan generation, quizzes, interview evaluation, job tracking, and user progress.

## Tech Stack

- FastAPI (ASGI web framework)
- Uvicorn (ASGI server)
- Pydantic / pydantic-settings (validation & configuration)
- Supabase (authentication and data storage)
- OpenAI / Groq and other external APIs (AI and content integrations)
- PyMuPDF, python-docx (resume/document parsing)
- NLTK (NLP utilities)

## Project Structure

- `app/main.py` – FastAPI application entrypoint and router registration
- `app/core/config.py` – application settings (project name, version, CORS)
- `app/routers/` – feature-specific routers:
  - `auth.py` – user registration and login (Supabase auth)
  - `resume.py` – resume upload and analysis
  - `plan.py` – learning plan generation
  - `quiz.py` – quiz submission and feedback
  - `interview.py` – interview submission and scoring
  - `jobs.py` – saving and retrieving tracked jobs
  - `progress.py` – overall readiness and dashboard metrics
  - `evaluate.py` – additional evaluation utilities
- `app/ROUTING_SHEET.md` – detailed documentation of request/response payloads and UI transitions
- `.env.example` – example environment variables required to run the backend
- `requirements.txt` – Python dependencies for the backend

## Setup

1. **Clone the repository** (if you haven’t already) and open the project in your terminal.

2. **Create & activate a virtual environment** (from the `backend` folder):

   ```bash
   cd backend
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS / Linux
   source .venv/bin/activate
   ```

3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:

   - Copy `.env.example` to `.env` in the `backend` directory.
   - Replace the example values with your own credentials and keys:
     - `SUPABASE_URL`
     - `SUPABASE_SERVICE_ROLE_KEY`
     - `OPENAI_API_KEY` / `GROQ_API_KEY` (if used)
     - Other API keys such as `GOOGLE_API_KEY`, `YOUTUBE_API_KEY`, etc.
   - Do **not** commit your `.env` file.

## Running the Server

From the `backend` directory (with the virtual environment activated):

```bash
uvicorn app.main:app --reload
```

By default, the API will be available at:

- `http://127.0.0.1:8000/`
- Interactive docs: `http://127.0.0.1:8000/docs`

## Available Routes (Overview)

The FastAPI app registers the following router groups:

- `/auth` – authentication routes (register, login)
- `/resume` – resume upload and analysis
- `/plan` – learning plan generation
- `/quiz` – quiz submission and scoring
- `/interview` – interview evaluation
- `/jobs` – job tracking (save and list jobs)
- `/progress` – user progress and readiness metrics
- `/evaluate` – additional evaluation utilities

The root endpoint:

- `GET /` – health check returning the API name and status.

For detailed payload and response shapes (including example JSON and UI transitions), see `app/ROUTING_SHEET.md`.

## Configuration Notes

- CORS origins are controlled via `CORS_ORIGINS` in `app/core/config.py` and default to allowing all origins (`"*"`). Adjust this for production deployments.
- Settings are loaded via `pydantic-settings` from the `.env` file in the `backend` directory.

## Troubleshooting

**Error: timed out when calling Supabase (India Region)**

If you experience database connection timeouts during local development, your ISP may be blocking the Supabase DNS resolution.

**Fix:** Change your system DNS to Cloudflare (`1.1.1.1` and `1.0.0.1`) or use a VPN. After changing DNS, run:

```bash
ipconfig /flushdns
```

and then restart your development server.
