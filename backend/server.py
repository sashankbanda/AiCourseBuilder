from fastapi import FastAPI, APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
import bcrypt
import jwt
# CHANGE 1: Remove OpenAI and import Google's library
# from openai import AsyncOpenAI
import google.generativeai as genai
import asyncio
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# CHANGE 2: Configure the Google Gemini client
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
db_client = AsyncIOMotorClient(mongo_url)
db = db_client[os.environ['DB_NAME']]

# JWT secret key
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-here')
JWT_ALGORITHM = 'HS256'

# Security
security = HTTPBearer(auto_error=False)
app = FastAPI()
api_router = APIRouter(prefix="/api")

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Pydantic Models (in correct order)
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    email: str
    password_hash: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class Video(BaseModel):
    title: str
    url: str
    thumbnail: Optional[str] = None

class Lesson(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    content: str
    videos: List[Video] = []
    code_examples: Optional[str] = None

class Quiz(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question: str
    options: List[str]
    correct_answer: str
    explanation: Optional[str] = None

class Course(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    topic: str
    title: str
    description: str
    lessons: List[Lesson] = []
    quizzes: List[Quiz] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completion_status: str = "not_started"

class CourseGenerate(BaseModel):
    topic: str

class QuizSubmission(BaseModel):
    course_id: str
    user_id: str
    answers: List[str]

class QuizResult(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    course_id: str
    score: int
    total_questions: int
    answers: List[str]
    correct_answers: List[str]
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Helper functions
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str) -> str:
    payload = {'user_id': user_id, 'exp': datetime.now(timezone.utc).timestamp() + 86400}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = None) -> Optional[str]:
    if not credentials:
        return None
    try:
        token = credentials.credentials if hasattr(credentials, 'credentials') else str(credentials)
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get('user_id')
    except (jwt.InvalidTokenError, AttributeError):
        return None

# CHANGE 3: Rewrite the LLM function to use Gemini
async def generate_course_with_llm(topic: str) -> Dict[str, Any]:
    """Generate course content using Google Gemini"""
    
    # Combine the system and user prompts into a single prompt for Gemini
    prompt = f"""
    You are an expert course creator. Generate a comprehensive mini-course about '{topic}'.
    The course should include 3-4 detailed lessons and a total of 15-20 quiz questions.
    Focus on practical knowledge and real-world applications.

    Always respond with valid JSON in exactly this format:
    {{
        "title": "Course Title",
        "description": "Brief course description",
        "lessons": [
            {{
                "title": "Lesson 1 Title",
                "content": "Detailed lesson content with explanations, examples, and key concepts. Use markdown formatting.",
                "code_examples": "Code examples if applicable (use markdown code blocks)",
                "video_queries": ["specific YouTube search query 1", "specific YouTube search query 2"]
            }}
        ],
        "quizzes": [
            {{
                "question": "Clear question text",
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "correct_answer": "Option A",
                "explanation": "Why this answer is correct"
            }}
        ]
    }}
    """

    try:
        # Initialize the model
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        # Set generation config to ensure JSON output
        generation_config = genai.types.GenerationConfig(response_mime_type="application/json")

        # Generate content
        response = await model.generate_content_async(prompt, generation_config=generation_config)
        
        response_text = response.text
        logger.info(f"LLM Response length: {len(response_text)}")
        
        try:
            course_data = json.loads(response_text)
            logger.info(f"Parsed course data keys: {list(course_data.keys())}")
            
            lessons = [
                Lesson(
                    title=lesson_data.get('title', 'Untitled Lesson'),
                    content=lesson_data.get('content', ''),
                    videos=[
                        Video(
                            title=f"Video: {query}",
                            url=f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}",
                            thumbnail="https://picsum.photos/1280/720"
                        ) for query in lesson_data.get('video_queries', [])
                    ],
                    code_examples=lesson_data.get('code_examples')
                ) for lesson_data in course_data.get('lessons', [])
            ]
            
            quizzes = [
                Quiz(**quiz_data) for quiz_data in course_data.get('quizzes', [])
            ]
            
            logger.info(f"Successfully created {len(lessons)} lessons and {len(quizzes)} quizzes")
            
            return {
                "title": course_data.get('title', f'Course: {topic}'),
                "description": course_data.get('description', f'A comprehensive course about {topic}'),
                "lessons": lessons,
                "quizzes": quizzes
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {response_text}")
            raise HTTPException(status_code=500, detail="Failed to parse LLM response.")
            
    except Exception as e:
        logger.error(f"Error generating course from LLM: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate course: {str(e)}")

# --- All endpoints below this line remain the same ---

# Authentication endpoints
@api_router.post("/auth/register")
async def register(user_data: UserCreate):
    if await db.users.find_one({"username": user_data.username}):
        raise HTTPException(status_code=400, detail="Username already exists")
    user = User(username=user_data.username, email=user_data.email, password_hash=hash_password(user_data.password))
    await db.users.insert_one(user.dict())
    token = create_token(user.id)
    return {"token": token, "user": {"id": user.id, "username": user.username, "email": user.email}}

@api_router.post("/auth/login")
async def login(user_data: UserLogin):
    user_doc = await db.users.find_one({"username": user_data.username})
    if not user_doc or not verify_password(user_data.password, user_doc['password_hash']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(user_doc['id'])
    return {"token": token, "user": {"id": user_doc['id'], "username": user_doc['username'], "email": user_doc['email']}}

# Course endpoints
@api_router.post("/courses/generate", response_model=Course)
async def generate_course(course_data: CourseGenerate, credentials: HTTPAuthorizationCredentials = Depends(security)):
    user_id = await get_current_user(credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    generated_content = await generate_course_with_llm(course_data.topic)
    course = Course(user_id=user_id, topic=course_data.topic, **generated_content)
    return course

@api_router.post("/courses/save")
async def save_course(course: Course, credentials: HTTPAuthorizationCredentials = Depends(security)):
    user_id = await get_current_user(credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    course_dict = course.dict()
    course_dict['created_at'] = course_dict['created_at'].isoformat()
    await db.courses.insert_one(course_dict)
    return {"message": "Course saved successfully", "course_id": course.id}

@api_router.get("/courses", response_model=List[Course])
async def get_courses(credentials: HTTPAuthorizationCredentials = Depends(security)):
    user_id = await get_current_user(credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    courses_cursor = db.courses.find({"user_id": user_id})
    return [Course(**course) async for course in courses_cursor]

@api_router.get("/courses/{course_id}", response_model=Course)
async def get_course(course_id: str, credentials: HTTPAuthorizationCredentials = Depends(security)):
    user_id = await get_current_user(credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    course_doc = await db.courses.find_one({"id": course_id, "user_id": user_id})
    if not course_doc:
        raise HTTPException(status_code=404, detail="Course not found")
    return Course(**course_doc)

@api_router.post("/quiz/submit")
async def submit_quiz(submission: QuizSubmission, credentials: HTTPAuthorizationCredentials = Depends(security)):
    user_id = await get_current_user(credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    course_doc = await db.courses.find_one({"id": submission.course_id})
    if not course_doc:
        raise HTTPException(status_code=404, detail="Course not found")
    correct_answers = [quiz['correct_answer'] for quiz in course_doc['quizzes']]
    score = sum(1 for i, answer in enumerate(submission.answers) if i < len(correct_answers) and answer == correct_answers[i])
    result = QuizResult(user_id=user_id, course_id=submission.course_id, score=score, total_questions=len(correct_answers), answers=submission.answers, correct_answers=correct_answers)
    result_dict = result.dict()
    result_dict['submitted_at'] = result_dict['submitted_at'].isoformat()
    await db.quiz_results.insert_one(result_dict)
    percentage = round((score / len(correct_answers)) * 100, 2) if correct_answers else 0
    return {"result": result, "percentage": percentage}

@api_router.get("/quiz/results/{course_id}")
async def get_quiz_results(course_id: str, credentials: HTTPAuthorizationCredentials = Depends(security)):
    user_id = await get_current_user(credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    results_cursor = db.quiz_results.find({"course_id": course_id, "user_id": user_id})
    return [QuizResult(**res) async for res in results_cursor]

@api_router.get("/")
async def root():
    return {"message": "Mini Course Generator API"}

app.include_router(api_router)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    db_client.close()