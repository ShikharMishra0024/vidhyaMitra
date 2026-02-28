from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from .routers import resume, evaluate, plan, quiz, interview, jobs, progress, auth

app: FastAPI = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)
app.add_middleware(
    middleware_class=CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(resume.router, prefix="/resume", tags=["resume"])
app.include_router(evaluate.router, prefix="/evaluate", tags=["evaluate"])
app.include_router(plan.router, prefix="/plan", tags=["plan"])
app.include_router(quiz.router, prefix="/quiz", tags=["quiz"])
app.include_router(interview.router, prefix="/interview", tags=["interview"])
app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
app.include_router(progress.router, prefix="/progress", tags=["progress"])
app.include_router(auth.router, prefix="/auth", tags=["authentication"])

@app.get(path="/")
def root() -> dict[str, str]:
    return {"name": "Vidyamitra API", "status": "ok"}