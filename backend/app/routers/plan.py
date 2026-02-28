import os
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from supabase import create_client, Client
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

# Initialize Clients & Keys
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
openai_client = AsyncOpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1" # This tricks the OpenAI library into talking to Groq!
)

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

router = APIRouter()

class PlanRequest(BaseModel):
    user_id: str
    target_role: str
    skill_gaps: list[str] # e.g., ["React Hooks", "FastAPI Deployment"]

@router.post("/generate")
async def generate_training_plan(request: PlanRequest):
    """
    Generates a personalized training plan using GPT-4, fetches relevant 
    YouTube tutorials, and grabs contextual images from Pexels.
    """
    try:

        # 1. Handle the Empty String / Auto-Fetch Logic
        if not request.target_role or request.target_role.strip() == "" or request.skill_gaps == []:
            
            # Fetch the user's latest resume evaluation
            db_query = supabase.table("resume_evaluations").select("analysis_result").eq("user_id", request.user_id).order("created_at", desc=True).limit(1).execute()
            
            # "else return user not exist" logic:
            if not db_query.data:
                raise HTTPException(status_code=404, detail="User resume profile not found. Please upload a resume first to auto-detect your skill gaps. or provide a target role and skill gaps manually.")
            
            analysis = db_query.data[0].get("analysis_result", {})
            request.skill_gaps = analysis.get("skill_gaps", [])
            request.target_role = analysis.get("target_role_evaluated", analysis.get("suggested_roles", ["professional"])[0].strip()) # Fallback to first suggested role or "professional"

            if not request.skill_gaps or request.target_role.strip() == "":
                raise HTTPException(status_code=400, detail="No specific skill gaps were found in your profile. Please provide a manual target role.")



        # 1. OpenAI (GPT-4): Generate the structured roadmap
        prompt = f"Create a short, 3-step learning roadmap for a user transitioning to {request.target_role}. Focus on these skill gaps: {', '.join(request.skill_gaps)}."
        
        completion = await openai_client.chat.completions.create(
            model="llama-3.3-70b-versatile", # Or gpt-4-turbo / gpt-4o for faster/cheaper JSON processing
            messages=[{"role": "system", "content": "You are an expert career counselor."},
                      {"role": "user", "content": prompt}]
        )
        roadmap_text = completion.choices[0].message.content

        # 2. YouTube API: Fetch top tutorials for the first skill gap
        youtube_videos = []
        for gap in request.skill_gaps:
            primary_gap = gap
            youtube_url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=3&q={primary_gap}+tutorial&type=video&key={YOUTUBE_API_KEY}"
            
            async with httpx.AsyncClient() as client:
                yt_response = await client.get(youtube_url)
                if yt_response.status_code == 200:
                    for item in yt_response.json().get("items", []):
                        youtube_videos.append({
                            "title": item["snippet"]["title"],
                            "video_id": item["id"]["videoId"],
                            "url": f"https://www.youtube.com/watch?v={item['id']['videoId']}"
                        })

        # 3. Pexels API: Fetch a motivational or domain-specific image
        dashboard_image = None
        pexels_url = f"https://api.pexels.com/v1/search?query={request.target_role}&per_page=1"
        
        async with httpx.AsyncClient() as client:
            px_response = await client.get(pexels_url, headers={"Authorization": PEXELS_API_KEY})
            if px_response.status_code == 200 and px_response.json().get("photos"):
                dashboard_image = px_response.json()["photos"][0]["src"]["medium"]

        # 4. Save the combined plan to Supabase
        plan_data = {
            "user_id": request.user_id,
            "target_role": request.target_role,
            "roadmap": roadmap_text,
            "recommended_videos": youtube_videos,
            "dashboard_image_url": dashboard_image
        }
        
        # Note: You will need a 'training_plans' table in Supabase
        db_response = supabase.table("training_plans").insert(plan_data).execute()

        return {
            "status": "success",
            "message": "Training plan generated with external resources.",
            "data": plan_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating plan: {str(e)}")