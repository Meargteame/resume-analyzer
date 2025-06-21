from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import JSONResponse
import os
import aiofiles
import aiohttp
import uuid
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from auth import get_current_user
import mimetypes
from pathlib import Path

# Router
upload_router = APIRouter()

# Configuration
UPLOAD_DIR = "/app/uploads"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {".pdf"}
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://n8n:5678/webhook/resume-upload")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/resume_analyzer")

# Create upload directory if it doesn't exist
os.makedirs(UPLOAD_DIR, exist_ok=True)

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(DATABASE_URL)

def validate_file(file: UploadFile) -> None:
    """Validate uploaded file"""
    # Check file extension
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Only {', '.join(ALLOWED_EXTENSIONS)} files are supported."
        )
    
    # Check MIME type
    mime_type = mimetypes.guess_type(file.filename)[0]
    if mime_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only PDF files are allowed."
        )

async def save_file(file: UploadFile) -> str:
    """Save uploaded file and return the file path"""
    # Generate unique filename
    file_extension = Path(file.filename).suffix.lower()
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    # Check file size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB."
        )
    
    # Save file
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(content)
    
    return file_path

async def store_resume_record(filename: str, original_filename: str, file_path: str, user_id: int) -> int:
    """Store resume record in database"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    INSERT INTO resumes (filename, analysis_status, uploaded_at)
                    VALUES (%s, %s, %s)
                    RETURNING id
                """, (original_filename, 'pending', datetime.utcnow()))
                
                resume_id = cursor.fetchone()['id']
                conn.commit()
                return resume_id
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

async def trigger_n8n_workflow(file_path: str, resume_id: int, original_filename: str):
    """Trigger n8n workflow via webhook"""
    try:
        webhook_data = {
            "resume_id": resume_id,
            "file_path": file_path,
            "filename": original_filename,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(N8N_WEBHOOK_URL, json=webhook_data) as response:
                if response.status == 200:
                    result = await response.json()
                    return result
                else:
                    error_text = await response.text()
                    raise HTTPException(
                        status_code=500,
                        detail=f"n8n webhook failed: {response.status} - {error_text}"
                    )
    except aiohttp.ClientError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to connect to n8n webhook: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error triggering n8n workflow: {str(e)}"
        )

@upload_router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload a PDF resume for analysis
    
    - **file**: PDF file to upload (max 10MB)
    - Returns: Upload confirmation with resume ID
    """
    try:
        # Validate file
        validate_file(file)
        
        # Save file
        file_path = await save_file(file)
        
        # Store record in database
        resume_id = await store_resume_record(
            filename=os.path.basename(file_path),
            original_filename=file.filename,
            file_path=file_path,
            user_id=current_user['id']
        )
        
        # Trigger n8n workflow
        try:
            workflow_result = await trigger_n8n_workflow(file_path, resume_id, file.filename)
        except HTTPException as e:
            # Update status to failed
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            "UPDATE resumes SET analysis_status = %s WHERE id = %s",
                            ('failed', resume_id)
                        )
                        conn.commit()
            except:
                pass  # Don't fail the whole request if status update fails
            
            raise e
        
        return JSONResponse(
            status_code=201,
            content={
                "message": "Resume uploaded successfully",
                "resume_id": resume_id,
                "filename": file.filename,
                "status": "processing",
                "workflow_triggered": True,
                "workflow_result": workflow_result
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )

@upload_router.get("/upload/status/{resume_id}")
async def get_upload_status(
    resume_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Get the status of a resume upload/analysis"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT id, filename, analysis_status, uploaded_at, 
                           full_name, email, phone, skills, experience_years, last_job_title
                    FROM resumes 
                    WHERE id = %s
                """, (resume_id,))
                
                resume = cursor.fetchone()
                if not resume:
                    raise HTTPException(status_code=404, detail="Resume not found")
                
                return dict(resume)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching status: {str(e)}")

@upload_router.post("/webhook/analysis-complete")
async def analysis_complete_webhook(data: dict):
    """
    Webhook endpoint for n8n to update resume analysis results
    This endpoint will be called by n8n when analysis is complete
    """
    try:
        resume_id = data.get('resume_id')
        analysis_results = data.get('analysis_results', {})
        
        if not resume_id:
            raise HTTPException(status_code=400, detail="Missing resume_id")
        
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Update resume with analysis results
                cursor.execute("""
                    UPDATE resumes SET
                        full_name = %s,
                        email = %s,
                        phone = %s,
                        skills = %s,
                        experience_years = %s,
                        last_job_title = %s,
                        raw_text = %s,
                        analysis_status = %s,
                        updated_at = %s
                    WHERE id = %s
                """, (
                    analysis_results.get('full_name'),
                    analysis_results.get('email'),
                    analysis_results.get('phone'),
                    analysis_results.get('skills', []),
                    analysis_results.get('experience_years'),
                    analysis_results.get('last_job_title'),
                    analysis_results.get('raw_text'),
                    'completed',
                    datetime.utcnow(),
                    resume_id
                ))
                
                conn.commit()
        
        return {"message": "Analysis results updated successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        # Update status to failed
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "UPDATE resumes SET analysis_status = %s WHERE id = %s",
                        ('failed', data.get('resume_id'))
                    )
                    conn.commit()
        except:
            pass
        
        raise HTTPException(status_code=500, detail=f"Error updating analysis: {str(e)}")
