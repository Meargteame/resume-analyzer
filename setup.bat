@echo off
echo 🚀 Setting up Resume Analyzer...

REM Create .env file if it doesn't exist
if not exist .env (
    echo 📝 Creating .env file...
    copy .env.example .env
    echo ✅ Please update .env with your OpenAI API key
) else (
    echo ✅ .env file already exists
)

REM Create uploads directory
if not exist uploads mkdir uploads
echo ✅ Created uploads directory

REM Build and start services
echo 🐳 Building Docker containers...
docker-compose build

echo 🚀 Starting services...
docker-compose up -d

echo ⏳ Waiting for services to start...
timeout /t 30 /nobreak

REM Check service health
echo 🔍 Checking service health...
echo Backend API: http://localhost:8000
echo n8n: http://localhost:5678 (admin/admin)
echo pgAdmin: http://localhost:5050 (admin@admin.com/admin)

echo ✅ Setup complete!
echo.
echo 📋 Next steps:
echo 1. Update .env with your OpenAI API key
echo 2. Access n8n at http://localhost:5678 (admin/admin)
echo 3. Import the workflow from workflows/resume-analyzer-workflow.json
echo 4. Test the API endpoints
echo.
echo 🧪 Test the upload endpoint:
echo curl -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d "{\"username\":\"admin\",\"password\":\"admin123\"}"

pause
