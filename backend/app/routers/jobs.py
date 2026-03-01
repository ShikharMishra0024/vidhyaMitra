import os
import json
import urllib.parse
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
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
class JobLinksRequest(BaseModel):
    target_role: str
    location: str = "Remote"

class JobMatchRequest(BaseModel):
    user_id: str
    job_title: str
    job_description: str

class SaveJobRequest(BaseModel):
    user_id: str
    job_title: str
    company_name: str
    job_url: str
    match_score: Optional[int] = None

# --- Endpoints ---

@router.post("/generate-links")
async def generate_job_search_links(request: JobLinksRequest):
    """
    Generates intelligent, pre-filtered search URLs for major job portals 
    based on the user's target role and preferred location.
    """
    try:
        # URL-encode the parameters so spaces become '%20' or '+'
        encoded_role = urllib.parse.quote(request.target_role)
        encoded_location = urllib.parse.quote(request.location)
        
        # Specific formatting for Indeed which prefers '+' for spaces
        indeed_role = request.target_role.replace(" ", "+")
        indeed_location = request.location.replace(" ", "+")

        # Generate intelligent redirect links
        links = {
            "LinkedIn": f"https://www.linkedin.com/jobs/search/?keywords={encoded_role}&location={encoded_location}",
            "Indeed": f"https://www.indeed.com/jobs?q={indeed_role}&l={indeed_location}",
            "Glassdoor": f"https://www.glassdoor.com/Job/jobs.htm?sc.keyword={encoded_role}&locName={encoded_location}",
            "GoogleJobs": f"https://www.google.com/search?q={encoded_role}+jobs+in+{encoded_location}&ibp=htl;jobs"
        }

        return {
            "status": "success",
            "message": "Search links generated successfully.",
            "target_role": request.target_role,
            "location": request.location,
            "portals": links
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating links: {str(e)}")


@router.post("/match")
async def match_resume_to_job(request: JobMatchRequest):
    """
    User pastes a Job Description from LinkedIn/Indeed here.
    Fetches the user's latest resume evaluation and uses GPT-4 to calculate a match percentage.
    """
    try:
        db_query = supabase.table("resume_evaluations").select("analysis_result").eq("user_id", request.user_id).order("created_at", desc=True).limit(1).execute()
        
        if not db_query.data:
            raise HTTPException(status_code=404, detail="No resume found. Please upload a resume first.")
            
        user_skills = db_query.data[0]["analysis_result"].get("strengths", [])

        prompt = f"""
        You are an expert ATS (Applicant Tracking System) AI. 
        Evaluate how well the candidate's skills match the provided job description.
        
        Candidate's Known Skills: {user_skills}
        Job Title: "{request.job_title}"
        Job Description: "{request.job_description}"
        
        You MUST respond in strictly valid JSON format matching this schema exactly:
        {{
            "match_score_percentage": 75,
            "matching_skills": ["List of skills they have that match the job"],
            "missing_keywords": ["List of keywords/skills in the JD that the candidate lacks"],
            "resume_advice": "One short sentence on how to tailor their resume for this specific job."
        }}
        """

        completion = await openai_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a precise, JSON-outputting ATS AI. You MUST output ONLY raw JSON. No markdown, no formatting, no conversational text."},
                {"role": "user", "content": prompt}
            ]
        )
        
        try:
            match_data = json.loads(completion.choices[0].message.content)
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="AI failed to return valid JSON.")

        return {"status": "success", "match_data": match_data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error matching job: {str(e)}")


@router.post("/save")
async def save_job(request: SaveJobRequest):
    """Bookmarks an external job URL to the user's VidyāMitra profile."""
    try:
        db_response = supabase.table("saved_jobs").insert({
            "user_id": request.user_id,
            "job_title": request.job_title,
            "company_name": request.company_name,
            "job_url": request.job_url,
            "match_score": request.match_score
        }).execute()

        return {"status": "success", "message": "Job saved successfully.", "data": db_response.data[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving job: {str(e)}")


@router.get("/saved/{user_id}")
async def get_saved_jobs(user_id: str):
    """Retrieves all bookmarked jobs for a user."""
    try:
        response = supabase.table("saved_jobs").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        return {"status": "success", "saved_jobs": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching saved jobs: {str(e)}")