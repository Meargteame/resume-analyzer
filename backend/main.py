from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager

# Load environment variables
load_dotenv()

# Import route modules
from auth import auth_router, get_current_user
from upload import upload_router

app = FastAPI(
    title="Resume Analyzer API",
    description="AI-powered resume analysis system with n8n workflow integration",
    version="1.0.0"
)

# Security
security = HTTPBearer()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/resume_analyzer")

@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        yield conn
    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            conn.close()

def get_db_cursor():
    """Dependency to get database cursor"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            yield cursor

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(upload_router, prefix="/api", tags=["Upload"])

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Resume Analyzer API is running!",
        "version": "1.0.0",
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return {
        "api": "healthy",
        "database": db_status,
        "n8n_webhook": os.getenv("N8N_WEBHOOK_URL", "not configured")
    }

@app.get("/resumes")
async def get_resumes(
    skip: int = 0,
    limit: int = 10,
    current_user: dict = Depends(get_current_user),
    cursor = Depends(get_db_cursor)
):
    """Get all resumes with pagination"""
    try:
        cursor.execute("""
            SELECT id, filename, full_name, email, phone, skills, 
                   experience_years, last_job_title, uploaded_at, analysis_status
            FROM resumes 
            ORDER BY uploaded_at DESC 
            LIMIT %s OFFSET %s
        """, (limit, skip))
        
        resumes = cursor.fetchall()
        
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM resumes")
        total = cursor.fetchone()['count']
        
        return {
            "resumes": resumes,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching resumes: {str(e)}")

@app.get("/resumes/{resume_id}")
async def get_resume(
    resume_id: int,
    current_user: dict = Depends(get_current_user),
    cursor = Depends(get_db_cursor)
):
    """Get a specific resume by ID"""
    try:
        cursor.execute("""
            SELECT * FROM resumes WHERE id = %s
        """, (resume_id,))
        
        resume = cursor.fetchone()
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        return resume
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching resume: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
