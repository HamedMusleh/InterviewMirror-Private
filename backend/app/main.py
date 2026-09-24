import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import models
from app.modules.adaptive_follow_up.router import (
    router as adaptive_follow_up_router,
)
from app.modules.answer_analysis.router import router as answer_analysis_router
from app.modules.applications.router import router as applications_router
from app.modules.candidate_ranking.router import (
    router as candidate_ranking_router,
)
from app.modules.candidates.router import router as candidates_router
from app.modules.interview_answers.router import (
    router as interview_answers_router,
)
from app.modules.interview_context.router import (
    router as interview_context_router,
)
from app.modules.interview_conversation.router import (
    router as interview_conversation_router,
)
from app.modules.interview_flow.router import (
    router as interview_flow_router,
)
from app.modules.interviews.router import router as interviews_router
from app.modules.interview_stream.router import (
    router as interview_stream_router,
)
from app.modules.interview_questions.router import (
    router as interview_questions_router,
)
from app.modules.job_description.router import router as job_description_router
from app.modules.job_opportunities.router import (
    router as job_opportunities_router,
)
from app.modules.question_generation.router import (
    router as question_generation_router,
)
from app.modules.resume_matching.router import router as resume_matching_router
from app.modules.resume_parser.router import router as resume_parser_router
from app.modules.screening.router import router as screening_router
from app.modules.screening_criteria.router import (
    router as screening_criteria_router,
)
from app.modules.text_to_speech.router import router as text_to_speech_router
from app.modules.evaluation.router import router as evaluation_router
from app.modules.candidate_report.router import (
    router as candidate_report_router,
    reports_list_router as candidate_reports_list_router,
)
from app.modules.interview_details.router import (
    router as interview_details_router,
)
app = FastAPI(
    title="InterviewMirror",
    description="Backend services for resume screening and evaluation.",
    version="1.0.0",
)

configured_frontend_origins = os.getenv("FRONTEND_ORIGINS")
if configured_frontend_origins:
    frontend_origins = [
        origin.strip()
        for origin in configured_frontend_origins.split(",")
        if origin.strip()
    ]
else:
    frontend_origins = [
        os.getenv("FRONTEND_ORIGIN", "http://localhost:5173"),
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/hello")
async def hello():
    return {"message": "Hello World"}


@app.get("/")
async def root():
    return {"status": "ok", "message": "Service is running"}


@app.get("/api/status", tags=["Status"])
async def get_status():
    return {"status": "OK"}


app.include_router(resume_parser_router)
app.include_router(job_description_router)
app.include_router(job_opportunities_router)
app.include_router(applications_router)
app.include_router(candidates_router)
app.include_router(screening_router)
app.include_router(resume_matching_router)
app.include_router(interview_questions_router)
app.include_router(interview_answers_router)
app.include_router(interview_context_router)
app.include_router(interview_conversation_router)
app.include_router(interview_flow_router)
app.include_router(interviews_router)
app.include_router(interview_stream_router)
app.include_router(adaptive_follow_up_router)
app.include_router(question_generation_router)
app.include_router(text_to_speech_router)
app.include_router(screening_criteria_router)
app.include_router(answer_analysis_router)
app.include_router(candidate_ranking_router)
app.include_router(evaluation_router)
app.include_router(candidate_report_router)
app.include_router(candidate_reports_list_router)
app.include_router(interview_details_router)
