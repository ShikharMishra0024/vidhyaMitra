import os
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from supabase import create_client, Client
from dotenv import load_dotenv
from openai import AsyncOpenAI
import asyncio

load_dotenv()

# Initialize Clients
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
openai_client = AsyncOpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1" # This tricks the OpenAI library into talking to Groq!
)

router = APIRouter()

# --- Pydantic Models ---
class EvaluateSessionRequest(BaseModel):
    session_id: str
    user_id: str

# --- Endpoints ---

@router.post("/interview-summary")
async def evaluate_interview_session(request: EvaluateSessionRequest):
    """
    Fetches the completed answers from the database, evaluates the entire 
    interview session using GPT-4, and generates a dashboard summary.
    """
    try:
        # 1. Fetch the session data from Supabase
        db_query = supabase.table("interview_sessions").select("*").eq("id", request.session_id).eq("user_id", request.user_id).execute()
        
        if not db_query.data:
            raise HTTPException(status_code=404, detail="Interview session not found.")
            
        session_data = db_query.data[0]
        
        if session_data.get("status") != "pending_evaluation":
            raise HTTPException(status_code=400, detail="Session is not ready for evaluation or has already been evaluated.")

        questions = session_data.get("questions", [])
        answers = session_data.get("user_answers", [])

        # 2. Map questions to answers to build the transcript for the AI
        transcript = f"Target Role: {session_data.get('target_role')}\n\n"
        
        # Create a dictionary of answers for easy lookup by question_id
        answer_dict = {ans["question_id"]: ans["answer_text"] for ans in answers}

        # 3. Define an async helper function to evaluate a single answer
        async def evaluate_single_answer(q_id: str, q_text: str, ans_text: str, role: str):
            single_prompt = f"""
            You are an expert career coach evaluating a single job interview answer for a '{role}' position.
            
            Question: "{q_text}"
            Candidate Answer: "{ans_text}"
            
            You MUST respond in strictly valid JSON format matching this schema exactly:
            {{
                "question_id": "{q_id}",
                "scores": {{"tone": 0, "confidence": 0, "accuracy": 0}},
                "feedback": "2-3 sentences of specific, actionable feedback for this specific answer."
            }}
            """
            try:
                response = await openai_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": "You are a precise, JSON-outputting career coach AI. You MUST output ONLY raw JSON. No markdown, no formatting, no conversational text."},
                        {"role": "user", "content": single_prompt}
                    ]
                )
                return json.loads(response.choices[0].message.content)
            except Exception:
                # Fallback in case a single evaluation fails so the whole session doesn't crash
                return {
                    "question_id": q_id,
                    "scores": {"tone": 0, "confidence": 0, "accuracy": 0},
                    "feedback": "Evaluation failed for this specific answer."
                }

        # 4. Run all evaluations concurrently to save time
        evaluation_tasks = []
        for q in questions:
            q_id = q["id"]
            q_text = q["text"]
            ans_text = answer_dict.get(q_id, "No answer provided.")
            
            # Add the task to our list
            evaluation_tasks.append(
                evaluate_single_answer(q_id, q_text, ans_text, session_data.get('target_role'))
            )

        # Wait for all 5 GPT-4 calls to finish simultaneously
        individual_evaluations = await asyncio.gather(*evaluation_tasks)

        # 5. Generate the overall Dashboard Summary based on the individual results
        summary_prompt = f"""
        Review these individual evaluations for a candidate interviewing for '{session_data.get('target_role')}':
        {json.dumps(individual_evaluations)}
        
        Generate a final dashboard summary. You MUST respond in strictly valid JSON format matching this schema exactly:
        {{
            "overall_score_out_of_10": 8.5,
            "key_strengths": ["Strength 1", "Strength 2"],
            "areas_for_improvement": ["Area 1", "Area 2"],
            "final_verdict": "A short, encouraging summary of their overall interview performance."
        }}
        """
        
        summary_completion = await openai_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a precise, JSON-outputting career coach AI. You MUST output ONLY raw JSON. No markdown, no formatting, no conversational text."},
                {"role": "user", "content": summary_prompt}
            ]
        )
        
        try:
            dashboard_summary = json.loads(summary_completion.choices[0].message.content)
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="AI failed to return valid JSON for the summary.")

        # Combine them into the final payload structure your database and frontend expect
        ai_evaluation = {
            "individual_evaluations": individual_evaluations,
            "dashboard_summary": dashboard_summary
        }

        # 6. Update the Supabase session record
        db_response = supabase.table("interview_sessions").update({
            "evaluation_data": ai_evaluation,
            "status": "completed"
        }).eq("id", request.session_id).execute()

        # 7. Return the massive payload to the frontend for the Dashboard
        return {
            "status": "success",
            "message": "Interview session evaluated successfully.",
            "dashboard_data": ai_evaluation
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error evaluating interview session: {str(e)}")