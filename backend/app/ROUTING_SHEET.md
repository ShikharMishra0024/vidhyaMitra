# VidyāMitra API Routing & Integration Guide

This document outlines all backend endpoints, the expected data shapes (Payload / Response), and the intended UI flow (Transition). All routes below are relative to the FastAPI base URL (for example, `/auth/login`).

---

## 🔐 1. Authentication (`/auth`)

### POST `/auth/register`

- **Payload (JSON body):**
  ```json
  {
    "email": "user@example.com",
    "password": "securepassword123",
    "firstName": "Sameer",
    "lastName": "Dwivedi",
    "phone": "+918843......" // optional
  }
  ```

- **Response (on success):**
  ```json
  {
    "message": "User registered successfully. Please check email for verification if enabled.",
    "user_id": "uuid-string"
  }
  ```

- **UI Transition:** Registration success ➔ Show success toast ➔ Optionally redirect to Login screen.

---

### POST `/auth/login`

- **Payload (JSON body):**
  ```json
  {
    "email": "user@example.com",
    "password": "securepassword123"
  }
  ```

- **Response (on success):**
  ```json
  {
    "access_token": "<jwt-access-token>",
    "refresh_token": "<jwt-refresh-token>",
    "token_type": "bearer",
    "user_info": {
      "id": "uuid-string",
      "email": "user@example.com",
      "username": "optional-username-or-null",
      "firstName": "Sameer",
      "lastName": "Dwivedi"
    }
  }
  ```

- **UI Transition:** Login success ➔ Store `access_token` (and `refresh_token`) in secure storage / auth context ➔ Navigate to main Dashboard.

---

## 📄 2. Onboarding & Resume (`/resume`)

### POST `/resume/upload`

- **Payload (multipart/form-data):**
  - `file`: PDF or DOCX resume file
  - `user_id`: `"uuid-string"`
  - `target_role` (optional): `"Data Engineer"`

- **Response (on success):**
  ```json
  {
    "status": "success",
    "message": "Resume successfully processed. Ready for roadmap generation.",
    "data": {
      // Row from Supabase `resume_evaluations` table, including
      // "analysis_result" with strengths, target_role_evaluated, suggested_roles, skill_gaps, etc.
    },
    "next_steps": {
      "action": "generate_plan",
      "endpoint": "/api/plan/generate",
      "payload_required": {
        "user_id": "uuid-string",
        "target_role": "Data Engineer",
        "skill_gaps": ["Docker", "Kubernetes"]
      }
    }
  }
  ```

- **UI Transition:**
  - Upload success ➔ Store `analysis_result` (strengths, target_role_evaluated, suggested_roles, skill_gaps) in global state.
  - Prepare/auto-fill payload for `/plan/generate` ➔ Navigate to Learning Plan screen.

---

### GET `/resume/history/{user_id}`

- **Payload:**
  - Path param: `user_id` (`"uuid-string"`)

- **Response:**
  ```json
  {
    "status": "success",
    "user_id": "uuid-string",
    "evaluations": [
      {
        "id": "uuid-string",
        "filename": "cv.pdf",
        "analysis_result": {
          "strengths": ["Python", "SQL"],
          "target_role_evaluated": "Data Engineer",
          "suggested_roles": ["Backend Developer", "Data Analyst"],
          "skill_gaps": ["Docker", "Kubernetes"]
        },
        "created_at": "2024-01-01T12:00:00Z"
      }
    ]
  }
  ```

- **UI Transition:** Data fetched ➔ Render past resume uploads and analyses (history list / detail modal).

---

## 🛣️ 3. Learning Plan (`/plan`)

### POST `/plan/generate`

- **Payload (JSON body):**
  ```json
  {
    "user_id": "uuid-string",
    "target_role": "Data Engineer",      // can be "" to auto-detect
    "skill_gaps": ["Docker", "Kubernetes"] // can be [] to auto-detect
  }
  ```

  - If `target_role` is empty **or** `skill_gaps` is empty, backend auto-fetches the latest resume evaluation for this user and fills them from `analysis_result`.

- **Response (on success):**
  ```json
  {
    "status": "success",
    "message": "Training plan generated with external resources.",
    "data": {
      "user_id": "uuid-string",
      "target_role": "Data Engineer (Upskilling)",
      "roadmap": "...free-text roadmap from AI...",
      "recommended_videos": [
        {
          "title": "Docker for Beginners",
          "video_id": "yt-video-id",
          "url": "https://www.youtube.com/watch?v=..."
        }
      ],
      "dashboard_image_url": "https://images.pexels.com/..."
    }
  }
  ```

- **UI Transition:** Plan generated ➔ Render roadmap text/sections + YouTube cards + hero image on Learning Plan / Roadmap UI.

---

## 📊 4. Quizzes (`/quiz`)

### POST `/quiz/generate`

- **Payload (JSON body):**
  ```json
  {
    "user_id": "uuid-string",
    "topic": "Docker basics",
    "difficulty": "intermediate", // one of: beginner, intermediate, advanced
    "num_questions": 5
  }
  ```

- **Response (on success):**
  ```json
  {
    "status": "success",
    "quiz_id": "uuid-string",
    "topic": "Docker basics",
    "questions": [
      {
        "id": "uuid-question-id",
        "question_text": "What is Docker?",
        "options": ["Option A", "Option B", "Option C", "Option D"]
      }
    ]
  }
  ```

- **UI Transition:** Quiz generated ➔ Navigate to Quiz screen and render `questions` with radio/MCQ inputs. Persist `quiz_id` for later submission.

---

### POST `/quiz/submit`

- **Payload (JSON body):**
  ```json
  {
    "quiz_id": "uuid-string",
    "user_id": "uuid-string",
    "answers": [
      {
        "question_id": "uuid-question-id",
        "selected_option": "To manage cluster resources"
      }
    ]
  }
  ```

- **Response (on success):**
  ```json
  {
    "status": "success",
    "message": "Quiz graded successfully.",
    "score": "4/5",
    "score_percentage": 80.0,
    "detailed_results": [
      {
        "question_id": "uuid-question-id",
        "question_text": "...",
        "user_answer": "To manage cluster resources",
        "correct_answer": "To package applications into containers",
        "is_correct": true,
        "explanation": "Great job! Review resource management concepts."
      }
    ]
  }
  ```

- **UI Transition:** Quiz graded ➔ Show results page or modal (score, per-question feedback) ➔ Option to retry, review answers, or go back to Dashboard.

---

### GET `/quiz/history/{user_id}`

- **Payload:** path param `user_id`.

- **Response:**
  ```json
  {
    "status": "success",
    "history": [
      {
        "id": "quiz-id",
        "topic": "Docker basics",
        "difficulty": "intermediate",
        "score_percentage": 80.0,
        "created_at": "2024-01-01T12:00:00Z"
      }
    ]
  }
  ```

- **UI Transition:** Data fetched ➔ Render quiz history list (topic, difficulty, score, date) with optional detail view.

---

## 🎤 5. Interviews (`/interview`)

### POST `/interview/start`

- **Payload (JSON body):**
  ```json
  {
    "user_id": "uuid-string",
    "target_role": "Data Engineer" // can be "" to auto-detect from resume
  }
  ```

- **Response (on success):**
  ```json
  {
    "status": "success",
    "session_id": "uuid-session-id",
    "questions": [
      {
        "id": "uuid-question-id",
        "text": "Tell me about a time you optimized a data pipeline."
      }
    ]
  }
  ```

- **UI Transition:** Session started ➔ Navigate to Interview screen ➔ Show questions one-by-one or all at once, tracking `session_id`.

---

### POST `/interview/submit-answers`

- **Payload (JSON body):**
  ```json
  {
    "session_id": "uuid-session-id",
    "user_id": "uuid-string",
    "answers": [
      {
        "question_id": "uuid-question-id",
        "answer_text": "I used Apache Spark for batch processing..."
      }
    ]
  }
  ```

- **Response (on success):**
  ```json
  {
    "status": "success",
    "message": "All answers submitted successfully. Ready for evaluation.",
    "session_id": "uuid-session-id",
    "next_steps": {
      "action": "evaluate_session",
      "endpoint": "/api/evaluate/interview-summary"
    }
  }
  ```

- **UI Transition:** Answers submitted ➔ Show "Submitted" confirmation ➔ Optionally auto-call `/evaluate/interview-summary` ➔ Navigate to Interview Feedback screen when evaluation is ready.

---

### GET `/interview/history/{user_id}`

- **Payload:** path param `user_id`.

- **Response:**
  ```json
  {
    "status": "success",
    "history": [
      {
        "id": "session-id",
        "target_role": "Data Engineer",
        "questions": [/* ... */],
        "evaluation_data": {/* ... when completed ... */},
        "status": "in_progress|pending_evaluation|completed",
        "created_at": "2024-01-01T12:00:00Z"
      }
    ]
  }
  ```

- **UI Transition:** Data fetched ➔ Render past interview sessions (status, scores, timestamps) with deep links into detailed feedback.

---

## 🧠 6. Interview Evaluation (`/evaluate`)

### POST `/evaluate/interview-summary`

- **Payload (JSON body):**
  ```json
  {
    "session_id": "uuid-session-id",
    "user_id": "uuid-string"
  }
  ```

- **Response (on success):**
  ```json
  {
    "status": "success",
    "message": "Interview session evaluated successfully.",
    "dashboard_data": {
      "individual_evaluations": [
        {
          "question_id": "uuid-question-id",
          "scores": {"tone": 7, "confidence": 8, "accuracy": 9},
          "feedback": "Specific, actionable feedback for this answer."
        }
      ],
      "dashboard_summary": {
        "overall_score_out_of_10": 8.5,
        "key_strengths": ["Strong communication", "Solid domain knowledge"],
        "areas_for_improvement": ["More concrete examples", "Clarify trade-offs"],
        "final_verdict": "Short, encouraging overall assessment."
      }
    }
  }
  ```

- **UI Transition:** Evaluation completed ➔ Render Interview Feedback UI (per-question breakdown + overall summary) ➔ Option to share/export or go back to Dashboard.

---

## 💼 7. Job Tracking & Matching (`/jobs`)

### POST `/jobs/generate-links`

- **Payload (JSON body):**
  ```json
  {
    "target_role": "Data Engineer",
    "location": "Remote" // or specific city
  }
  ```

- **Response:**
  ```json
  {
    "status": "success",
    "message": "Search links generated successfully.",
    "target_role": "Data Engineer",
    "location": "Remote",
    "portals": {
      "LinkedIn": "https://www.linkedin.com/jobs/search/?keywords=...",
      "Indeed": "https://www.indeed.com/jobs?q=...",
      "Glassdoor": "https://www.glassdoor.com/Job/jobs.htm?sc.keyword=...",
      "GoogleJobs": "https://www.google.com/search?q=..."
    }
  }
  ```

- **UI Transition:** Links generated ➔ Render portal buttons/cards ➔ On click, open external job boards in new tab.

---

### POST `/jobs/match`

- **Payload (JSON body):**
  ```json
  {
    "user_id": "uuid-string",
    "job_title": "Junior Data Engineer",
    "job_description": "Full pasted JD text from LinkedIn/Indeed/etc."
  }
  ```

- **Response:**
  ```json
  {
    "status": "success",
    "match_data": {
      "match_score_percentage": 85,
      "matching_skills": ["Python", "SQL"],
      "missing_keywords": ["Kubernetes", "Airflow"],
      "resume_advice": "One short sentence on how to tailor resume."
    }
  }
  ```

- **UI Transition:** Match calculated ➔ Show job-match score and lists (matching skills, missing keywords) ➔ Provide CTA to save this job or refine resume.

---

### POST `/jobs/save`

- **Payload (JSON body):**
  ```json
  {
    "user_id": "uuid-string",
    "job_title": "Junior Data Engineer",
    "company_name": "Tech Corp",
    "job_url": "https://linkedin.com/...",
    "match_score": 85
  }
  ```

- **Response:**
  ```json
  {
    "status": "success",
    "message": "Job saved successfully.",
    "data": {
      "id": "uuid-string",
      "user_id": "uuid-string",
      "job_title": "Junior Data Engineer",
      "company_name": "Tech Corp",
      "job_url": "https://linkedin.com/...",
      "match_score": 85
    }
  }
  ```

- **UI Transition:** Job saved ➔ Show toast/notification (no redirect needed) ➔ Optionally update local "Saved Jobs" list.

---

### GET `/jobs/saved/{user_id}`

- **Payload:** path param `user_id`.

- **Response:**
  ```json
  {
    "status": "success",
    "saved_jobs": [
      {
        "id": "uuid-string",
        "job_title": "Junior Data Engineer",
        "company_name": "Tech Corp",
        "job_url": "https://linkedin.com/...",
        "match_score": 85,
        "created_at": "2024-01-01T12:00:00Z"
      }
    ]
  }
  ```

- **UI Transition:** Data fetched ➔ Render Saved Jobs board/list with links and match scores.

---

## 📈 8. User Dashboard & Readiness (`/progress`)

### GET `/progress/dashboard/{user_id}`

- **Payload:** path param `user_id`.

- **Response:**
  ```json
  {
    "status": "success",
    "user_id": "uuid-string",
    "target_role": {
      "data": [
        { "target_role": "Data Engineer" }
      ]
    },
    "metrics": {
      "overall_readiness_score": 75.5,
      "knowledge_score": 80.0,          // from quizzes
      "communication_score": 70.0,      // from interviews
      "job_market_alignment": 85.0      // from saved job match scores
    },
    "activity_counts": {
      "quizzes_completed": 3,
      "interviews_completed": 2,
      "jobs_bookmarked": 5
    }
  }
  ```

- **UI Transition:** Data fetched ➔ Render main Dashboard UI: readiness gauge, metric cards, charts, and activity counts. Use `target_role` to label dashboard context (e.g., "Readiness for Data Engineer").

---

## 🌐 9. Health Check (Root)

### GET `/`

- **Response:**
  ```json
  {
    "name": "Vidyamitra API",
    "status": "ok"
  }
  ```
