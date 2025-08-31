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
from emergentintegrations.llm.chat import LlmChat, UserMessage
import asyncio
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT secret key (in production, use a more secure key)
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-here')
JWT_ALGORITHM = 'HS256'

# Security
security = HTTPBearer(auto_error=False)

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Pydantic Models
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
    completion_status: str = "not_started"  # not_started, in_progress, completed

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
    payload = {
        'user_id': user_id,
        'exp': datetime.now(timezone.utc).timestamp() + 86400  # 24 hours
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = None) -> Optional[str]:
    if not credentials:
        return None
    try:
        # credentials should be HTTPAuthorizationCredentials object
        token = credentials.credentials if hasattr(credentials, 'credentials') else str(credentials)
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get('user_id')
    except (jwt.InvalidTokenError, AttributeError):
        return None

async def generate_course_with_llm(topic: str) -> Dict[str, Any]:
    """Generate course content using LLM"""
    try:
        # Initialize LLM chat
        chat = LlmChat(
            api_key=os.environ.get('EMERGENT_LLM_KEY'),
            session_id=f"course-gen-{uuid.uuid4()}",
            system_message="""You are an expert course creator. Generate comprehensive mini-courses with 3-4 lessons.
            
            Always respond with valid JSON in exactly this format:
            {
                "title": "Course Title",
                "description": "Brief course description",
                "lessons": [
                    {
                        "title": "Lesson 1 Title",
                        "content": "Detailed lesson content with explanations, examples, and key concepts. Use markdown formatting.",
                        "code_examples": "Code examples if applicable (use markdown code blocks)",
                        "video_queries": ["specific YouTube search query 1", "specific YouTube search query 2"]
                    }
                ],
                "quizzes": [
                    {
                        "question": "Clear question text",
                        "options": ["Option A", "Option B", "Option C", "Option D"],
                        "correct_answer": "Option A",
                        "explanation": "Why this answer is correct"
                    }
                ]
            }
            
            Make content educational, engaging, and practical. Include 6-8 quiz questions total."""
        ).with_model("openai", "gpt-4o")
        
        # Create user message
        user_message = UserMessage(
            text=f"Create a comprehensive mini-course about '{topic}'. Include 3-4 detailed lessons and 6-8 quiz questions. Focus on practical knowledge and real-world applications."
        )
        
        # Send message and get response
        response = await chat.send_message(user_message)
        logger.info(f"LLM Response type: {type(response)}")
        logger.info(f"LLM Response length: {len(str(response))}")
        
        # Handle different response types and extract text
        if hasattr(response, 'content'):
            response_text = response.content
        elif hasattr(response, 'text'):
            response_text = response.text
        else:
            response_text = str(response)
        
        logger.info(f"Response text length: {len(response_text)}")
        logger.info(f"Response text first 200 chars: {response_text[:200]}")
        
        # Clean the response - remove markdown code blocks if present
        response_text = response_text.strip()
        if response_text.startswith('```json'):
            response_text = response_text[7:]  # Remove ```json
        if response_text.startswith('```'):
            response_text = response_text[3:]   # Remove ```
        if response_text.endswith('```'):
            response_text = response_text[:-3]  # Remove trailing ```
        response_text = response_text.strip()
        
        logger.info(f"Cleaned response text first 200 chars: {response_text[:200]}")
        
        # Parse JSON response
        try:
            logger.info(f"Attempting to parse JSON...")
            course_data = json.loads(response_text)
            logger.info(f"Parsed course data keys: {list(course_data.keys())}")
            
            # Convert to proper format
            lessons = []
            for lesson_data in course_data.get('lessons', []):
                # Generate mock YouTube videos based on queries
                videos = []
                for query in lesson_data.get('video_queries', []):
                    videos.append({
                        "title": f"Video: {query}",
                        "url": f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}",
                        "thumbnail": "https://img.youtube.com/vi/dQw4w9WgXcQ/maxresdefault.jpg"
                    })
                
                lesson = Lesson(
                    title=lesson_data.get('title', 'Untitled Lesson'),
                    content=lesson_data.get('content', ''),
                    videos=videos,
                    code_examples=lesson_data.get('code_examples')
                )
                lessons.append(lesson)
            
            # Convert quizzes
            quizzes = []
            for quiz_data in course_data.get('quizzes', []):
                quiz = Quiz(
                    question=quiz_data.get('question', ''),
                    options=quiz_data.get('options', []),
                    correct_answer=quiz_data.get('correct_answer', ''),
                    explanation=quiz_data.get('explanation', '')
                )
                quizzes.append(quiz)
            
            logger.info(f"Successfully created {len(lessons)} lessons and {len(quizzes)} quizzes")
            
            return {
                "title": course_data.get('title', f'Course: {topic}'),
                "description": course_data.get('description', f'A comprehensive course about {topic}'),
                "lessons": lessons,
                "quizzes": quizzes
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {response}")
            logger.error(f"JSON Error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate course content - invalid JSON response"
            )
        except Exception as e:
            logger.error(f"Error processing course data: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process course content: {str(e)}"
            )
            
    except Exception as e:
        logger.error(f"Error generating course: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate course: {str(e)}"
        )

# Authentication endpoints
@api_router.post("/auth/register")
async def register(user_data: UserCreate):
    # Check if user exists
    existing_user = await db.users.find_one({"username": user_data.username})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Create user
    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hash_password(user_data.password)
    )
    
    # Save to database
    user_dict = user.dict()
    await db.users.insert_one(user_dict)
    
    # Create token
    token = create_token(user.id)
    
    return {"token": token, "user": {"id": user.id, "username": user.username, "email": user.email}}

@api_router.post("/auth/login")
async def login(user_data: UserLogin):
    # Find user
    user_doc = await db.users.find_one({"username": user_data.username})
    if not user_doc or not verify_password(user_data.password, user_doc['password_hash']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create token
    token = create_token(user_doc['id'])
    
    return {"token": token, "user": {"id": user_doc['id'], "username": user_doc['username'], "email": user_doc['email']}}

# Course endpoints
@api_router.post("/courses/generate", response_model=Course)
async def generate_course(course_data: CourseGenerate, credentials: HTTPAuthorizationCredentials = Depends(security)):
    user_id = await get_current_user(credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Generate course using LLM
    generated_content = await generate_course_with_llm(course_data.topic)
    
    # Create course object
    course = Course(
        user_id=user_id,
        topic=course_data.topic,
        title=generated_content['title'],
        description=generated_content['description'],
        lessons=generated_content['lessons'],
        quizzes=generated_content['quizzes']
    )
    
    return course

@api_router.post("/courses/save")
async def save_course(course: Course, credentials: HTTPAuthorizationCredentials = Depends(security)):
    user_id = await get_current_user(credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Save course to database
    course_dict = course.dict()
    # Convert datetime objects to strings for MongoDB
    course_dict['created_at'] = course_dict['created_at'].isoformat() if isinstance(course_dict['created_at'], datetime) else course_dict['created_at']
    
    await db.courses.insert_one(course_dict)
    
    return {"message": "Course saved successfully", "course_id": course.id}

@api_router.get("/courses", response_model=List[Course])
async def get_courses(credentials: HTTPAuthorizationCredentials = Depends(security)):
    user_id = await get_current_user(credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Get user's courses
    courses = await db.courses.find({"user_id": user_id}).to_list(length=None)
    
    # Convert back to Course objects
    result = []
    for course_doc in courses:
        # Convert created_at back to datetime if it's a string
        if isinstance(course_doc.get('created_at'), str):
            course_doc['created_at'] = datetime.fromisoformat(course_doc['created_at'])
        result.append(Course(**course_doc))
    
    return result

@api_router.get("/courses/{course_id}", response_model=Course)
async def get_course(course_id: str, credentials: HTTPAuthorizationCredentials = Depends(security)):
    user_id = await get_current_user(credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Get specific course
    course_doc = await db.courses.find_one({"id": course_id, "user_id": user_id})
    if not course_doc:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Convert created_at back to datetime if it's a string
    if isinstance(course_doc.get('created_at'), str):
        course_doc['created_at'] = datetime.fromisoformat(course_doc['created_at'])
    
    return Course(**course_doc)

@api_router.post("/quiz/submit")
async def submit_quiz(submission: QuizSubmission, credentials: HTTPAuthorizationCredentials = Depends(security)):
    user_id = await get_current_user(credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Get course
    course_doc = await db.courses.find_one({"id": submission.course_id})
    if not course_doc:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Calculate score
    correct_answers = [quiz['correct_answer'] for quiz in course_doc['quizzes']]
    score = sum(1 for i, answer in enumerate(submission.answers) if i < len(correct_answers) and answer == correct_answers[i])
    
    # Create quiz result
    result = QuizResult(
        user_id=user_id,
        course_id=submission.course_id,
        score=score,
        total_questions=len(correct_answers),
        answers=submission.answers,
        correct_answers=correct_answers
    )
    
    # Save to database
    result_dict = result.dict()
    result_dict['submitted_at'] = result_dict['submitted_at'].isoformat() if isinstance(result_dict['submitted_at'], datetime) else result_dict['submitted_at']
    
    await db.quiz_results.insert_one(result_dict)
    
    return {"result": result, "percentage": round((score / len(correct_answers)) * 100, 2) if correct_answers else 0}

@api_router.get("/quiz/results/{course_id}")
async def get_quiz_results(course_id: str, credentials: HTTPAuthorizationCredentials = Depends(security)):
    user_id = await get_current_user(credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Get quiz results for course
    results = await db.quiz_results.find({"course_id": course_id, "user_id": user_id}).to_list(length=None)
    
    # Convert back to QuizResult objects
    result_objects = []
    for result_doc in results:
        if isinstance(result_doc.get('submitted_at'), str):
            result_doc['submitted_at'] = datetime.fromisoformat(result_doc['submitted_at'])
        result_objects.append(QuizResult(**result_doc))
    
    return result_objects

# Test endpoint
@api_router.get("/")
async def root():
    return {"message": "Mini Course Generator API"}

# Include the router in the main app
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
    client.close()