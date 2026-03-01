import os
import json
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from supabase import create_client, Client
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

# Initialize Clients
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
openai_client = AsyncOpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1" # This tricks the OpenAI library into talking to Groq!
)

router = APIRouter()

# --- Pydantic Models ---
class StartInterviewRequest(BaseModel):
    user_id: str
    target_role: str

class AnswerItem(BaseModel):
    question_id: str
    answer_text: str

class SubmitAllAnswersRequest(BaseModel):
    session_id: str
    user_id: str
    answers: List[AnswerItem]

# --- Endpoints ---

@router.post("/start")
async def start_interview_session(request: StartInterviewRequest):
    """
    Starts a new interview session by generating 5 role-specific questions.
    Assigns a unique ID to each question for reliable tracking.
    """
    try:
        # 1. validate input and handle empty target_role with auto-fetch logic
        if not request.target_role or request.target_role.strip() == "":
            
            # Fetch the user's latest resume evaluation
            db_query = supabase.table("resume_evaluations").select("analysis_result").eq("user_id", request.user_id).order("created_at", desc=True).limit(1).execute()
            
            # "else return user not exist" logic:
            if not db_query.data:
                raise HTTPException(status_code=404, detail="User resume profile not found. Please upload a resume first to auto-detect your skill gaps. or provide a target role and skill gaps manually.")
            
            analysis = db_query.data[0].get("analysis_result", {})
            request.target_role = analysis.get("target_role_evaluated", analysis.get("suggested_roles", ["professional"])[0].strip()) # Fallback to first suggested role or "professional"

            if not request.target_role or request.target_role.strip() == "":
                raise HTTPException(status_code=400, detail="No specific target role were found in your profile. Please provide a manual target role.")



        # 2. Ask GPT-4 to generate the questions
        prompt = f"""
        You are conducting a professional job interview for a '{request.target_role}' position. 
        Generate exactly 5 interview questions. Include a mix of technical, behavioral, and situational questions.
        
        You MUST respond in strictly valid JSON format matching this schema:
        {{
            "questions": [
                "Question 1 text...",
                "Question 2 text...",
                "Question 3 text...",
                "Question 4 text...",
                "Question 5 text..."
            ]
        }}
        """

        completion = await openai_client.chat.completions.create(
            model="llama-3.3-70b-versatile", 
            messages=[
                {"role": "system", "content": "You are a precise, JSON-outputting hiring manager AI. You MUST output ONLY raw JSON. No markdown, no formatting, no conversational text."},
                {"role": "user", "content": prompt}
            ]
        )
        
        # 3. Parse the AI Data
        try:
            ai_data = json.loads(completion.choices[0].message.content)
            raw_questions = ai_data.get("questions", [])
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="AI failed to return valid JSON.")

        # 4. Format questions with unique IDs
        formatted_questions = [
            {"id": str(uuid.uuid4()), "text": q_text} for q_text in raw_questions
        ]

        # 5. Save the new session to Supabase
        db_response = supabase.table("interview_sessions").insert({
            "user_id": request.user_id,
            "target_role": request.target_role,
            "questions": formatted_questions,
            "status": "in_progress"
        }).execute()

        return {
            "status": "success",
            "session_id": db_response.data[0]["id"],
            "questions": formatted_questions
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting interview: {str(e)}")


@router.post("/submit-answers")
async def submit_all_answers(submission: SubmitAllAnswersRequest):
    """
    Accepts all answers mapped to their question_ids at once.
    Saves them to the database session and marks it ready for evaluation.
    """
    try:
        # 1. Verify the session exists and belongs to the user
        db_query = supabase.table("interview_sessions").select("id").eq("id", submission.session_id).eq("user_id", submission.user_id).execute()
        if not db_query.data:
            raise HTTPException(status_code=404, detail="Interview session not found or unauthorized.")

        # 2. Format the answers into a JSON serializable list
        answers_data = [
            {"question_id": ans.question_id, "answer_text": ans.answer_text}
            for ans in submission.answers
        ]

        # 3. Update the Supabase session record
        db_response = supabase.table("interview_sessions").update({
            "user_answers": answers_data,
            "status": "pending_evaluation" # Setting state for the evaluate.py router to pick up
        }).eq("id", submission.session_id).execute()

        return {
            "status": "success",
            "message": "All answers submitted successfully. Ready for evaluation.",
            "session_id": submission.session_id,
            "next_steps": {
                "action": "evaluate_session",
                "endpoint": "/api/evaluate/interview-summary"
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting answers: {str(e)}")


@router.get("/history/{user_id}")
async def get_interview_history(user_id: str):
    """Fetches a user's past interview sessions."""
    try:
        response = supabase.table("interview_sessions").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        return {"status": "success", "history": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching history: {str(e)}")