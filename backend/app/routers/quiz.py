import os
import json
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict
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
class GenerateQuizRequest(BaseModel):
    user_id: str
    topic: str
    difficulty: str = "intermediate" # beginner, intermediate, advanced
    num_questions: int = 5

class QuizAnswerItem(BaseModel):
    question_id: str
    selected_option: str

class SubmitQuizRequest(BaseModel):
    quiz_id: str
    user_id: str
    answers: List[QuizAnswerItem]

# --- Endpoints ---

@router.post("/generate")
async def generate_quiz(request: GenerateQuizRequest):
    """
    Generates a multiple-choice quiz on a specific topic using GPT-4.
    Saves the questions and correct answers to the database.
    """
    try:
        prompt = f"""
        Create a multiple-choice quiz with exactly {request.num_questions} questions about '{request.topic}' at an '{request.difficulty}' level.
        
        You MUST respond in strictly valid JSON format matching this schema exactly:
        {{
            "questions": [
                {{
                    "question_text": "The question itself?",
                    "options": ["Option A", "Option B", "Option C", "Option D"],
                    "correct_answer": "The exact string of the correct option",
                    "explanation": "Why this is the correct answer"
                }}
            ]
        }}
        """

        completion = await openai_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a precise, JSON-outputting educational AI.You MUST output ONLY raw JSON. No markdown, no formatting, no conversational text."},
                {"role": "user", "content": prompt}
            ]
        )
        
        try:
            ai_data = json.loads(completion.choices[0].message.content)
            raw_questions = ai_data.get("questions", [])
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="AI failed to return valid JSON.")

        # Assign unique IDs to each question so the frontend can track them
        formatted_questions = []
        for q in raw_questions:
            q["id"] = str(uuid.uuid4())
            formatted_questions.append(q)

        # Save the new quiz session to Supabase
        db_response = supabase.table("quizzes").insert({
            "user_id": request.user_id,
            "topic": request.topic,
            "difficulty": request.difficulty,
            "questions": formatted_questions,
            "status": "pending"
        }).execute()

        # REMOVE the correct answers and explanations before sending to the frontend!
        # We don't want the user to cheat by inspecting the network payload.
        safe_questions = [
            {
                "id": q["id"], 
                "question_text": q["question_text"], 
                "options": q["options"]
            } 
            for q in formatted_questions
        ]

        return {
            "status": "success",
            "quiz_id": db_response.data[0]["id"],
            "topic": request.topic,
            "questions": safe_questions
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating quiz: {str(e)}")


@router.post("/submit")
async def submit_quiz(submission: SubmitQuizRequest):
    """
    Grades the submitted quiz by comparing user answers to the stored correct answers.
    Returns the score and explanations.
    """
    try:
        # 1. Fetch the quiz data (with the correct answers) from Supabase
        db_query = supabase.table("quizzes").select("*").eq("id", submission.quiz_id).eq("user_id", submission.user_id).execute()
        
        if not db_query.data:
            raise HTTPException(status_code=404, detail="Quiz not found.")
            
        quiz_data = db_query.data[0]
        
        if quiz_data.get("status") == "completed":
            raise HTTPException(status_code=400, detail="This quiz has already been submitted.")

        original_questions = quiz_data.get("questions", [])
        
        # 2. Grade the quiz programmatically (No AI needed here, saving time & money!)
        score = 0
        total_questions = len(original_questions)
        detailed_results = []
        
        # Convert user answers to a dictionary for easy lookup
        user_answers_dict = {ans.question_id: ans.selected_option for ans in submission.answers}

        for q in original_questions:
            q_id = q["id"]
            correct_ans = q["correct_answer"]
            user_ans = user_answers_dict.get(q_id, "No answer provided")
            
            is_correct = (user_ans == correct_ans)
            if is_correct:
                score += 1
                
            detailed_results.append({
                "question_id": q_id,
                "question_text": q["question_text"],
                "user_answer": user_ans,
                "correct_answer": correct_ans,
                "is_correct": is_correct,
                "explanation": q["explanation"]
            })

        final_score_percentage = (score / total_questions) * 100

        # 3. Update the database with the results
        db_response = supabase.table("quizzes").update({
            "score_percentage": final_score_percentage,
            "user_answers": [ans.model_dump() for ans in submission.answers],
            "detailed_results": detailed_results,
            "status": "completed"
        }).eq("id", submission.quiz_id).execute()

        return {
            "status": "success",
            "message": "Quiz graded successfully.",
            "score": f"{score}/{total_questions}",
            "score_percentage": final_score_percentage,
            "detailed_results": detailed_results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error grading quiz: {str(e)}")


@router.get("/history/{user_id}")
async def get_quiz_history(user_id: str):
    """Fetches a user's past quizzes and scores."""
    try:
        response = supabase.table("quizzes").select("id, topic, difficulty, score_percentage, created_at").eq("user_id", user_id).order("created_at", desc=True).execute()
        return {"status": "success", "history": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching quiz history: {str(e)}")