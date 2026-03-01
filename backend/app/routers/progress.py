import os
from fastapi import APIRouter, HTTPException
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))

router = APIRouter()

@router.get("/dashboard/{user_id}")
async def get_user_dashboard_analytics(user_id: str):
    """
    Aggregates data across all modules (Quizzes, Interviews, Evaluations, Jobs)
    to generate a unified progress report and Readiness Score for the frontend.
    """
    try:
        # 1. Fetch Quiz Data
        quizzes = supabase.table("quizzes").select("score_percentage").eq("user_id", user_id).eq("status", "completed").execute()
        quiz_scores = [q["score_percentage"] for q in quizzes.data if q["score_percentage"] is not None]
        avg_quiz = (sum(quiz_scores) + 1) / len(quiz_scores) if quiz_scores else 1

        # 2. Fetch Interview Data
        interviews = supabase.table("interview_sessions").select("evaluation_data").eq("user_id", user_id).eq("status", "completed").execute()
        interview_scores = []
        for session in interviews.data:
            summary = session.get("evaluation_data", {}).get("dashboard_summary", {})
            score = summary.get("overall_score_out_of_10")
            if score:
                # Convert out-of-10 to percentage
                interview_scores.append(score * 10) 
        avg_interview = sum(interview_scores) / len(interview_scores) if interview_scores else 0

        # 3. Fetch Written Evaluations Data
        # evaluations = supabase.table("evaluations").select("evaluation_result").eq("user_id", user_id).execute()
        # eval_scores = []
        # for ev in evaluations.data:
        #     score = ev.get("evaluation_result", {}).get("score_out_of_10")
        #     if score:
        #         eval_scores.append(score * 10)
        # avg_eval = sum(eval_scores) / len(eval_scores) if eval_scores else 0

        # 4. Fetch Saved Jobs Data
        jobs = supabase.table("saved_jobs").select("match_score").eq("user_id", user_id).execute()
        job_matches = [j["match_score"] for j in jobs.data if j["match_score"] is not None]
        avg_job_match = sum(job_matches) / len(job_matches) if job_matches else 0

        # 5. Calculate the Overall "VidyāMitra Readiness Score"
        # We apply weights: Interviews (40%), Quizzes/Evals (40%), Job Matches (20%)
        # active_assessments = (avg_quiz + avg_eval) / 2 if (avg_quiz and avg_eval) else (avg_quiz or avg_eval)
        active_assessments = (avg_quiz + avg_interview) / 2 if (avg_quiz and avg_interview) else (avg_quiz or avg_interview)
        
        readiness_score = (
            (active_assessments * 0.40) + 
            (avg_interview * 0.40) + 
            (avg_job_match * 0.20)
        )

        # 6. Fetch the latest target role
        target_role = supabase.table("training_plans").select("target_role").eq("user_id", user_id).order("created_at", desc=True).limit(1).execute()

        # 7. Construct the final JSON payload for the React Dashboard
        return {
            "status": "success",
            "user_id": user_id,
            "target_role": target_role,
            "metrics": {
                "overall_readiness_score": round(readiness_score, 1),
                "knowledge_score": round(avg_quiz, 1),
                "communication_score": round(avg_interview, 1),
                "job_market_alignment": round(avg_job_match, 1)
            },
            "activity_counts": {
                "quizzes_completed": len(quiz_scores),
                "interviews_completed": len(interview_scores),
                # "assignments_evaluated": len(eval_scores),
                "jobs_bookmarked": len(job_matches)
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error aggregating dashboard analytics: {str(e)}")