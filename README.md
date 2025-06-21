# 🎯 Resume Analyzer

AI-powered resume analysis system with FastAPI, n8n workflows, PostgreSQL, and OpenAI integration.

## 🏗️ Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Frontend  │───▶│   FastAPI   │───▶│     n8n     │───▶│   OpenAI    │
│    (Web)    │    │  (Backend)  │    │ (Workflow)  │    │     API     │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                           │                   │
                           ▼                   ▼
                   ┌─────────────┐    ┌─────────────┐
                   │ PostgreSQL  │    │ File Storage│
                   │ (Database)  │    │ (Uploads)   │
                   └─────────────┘    └─────────────┘
```

## 🚀 Features

- **🔐 JWT Authentication** - Secure user authentication
- **📄 PDF Upload** - Secure file upload with validation
- **🤖 AI Analysis** - OpenAI-powered resume parsing
- **🔄 Workflow Automation** - n8n-based processing pipeline
- **📊 Database Storage** - PostgreSQL with structured data
- **🐳 Docker Deployment** - Containerized services
- **📈 Admin Dashboard** - pgAdmin for database management

## 🛠️ Tech Stack

- **Backend**: FastAPI, Python 3.11
- **Database**: PostgreSQL 15
- **Workflow**: n8n
- **AI**: OpenAI GPT-3.5-turbo
- **Auth**: JWT with bcrypt
- **Deployment**: Docker Compose
- **Admin**: pgAdmin4

## 📋 Prerequisites

- Docker and Docker Compose
- OpenAI API key
- 10GB+ free disk space

## 🚀 Quick Start

### 1. Clone and Setup

```bash
git clone <your-repo>
cd resume-analyzer

# Run setup script
chmod +x setup.sh
./setup.sh

# OR on Windows
setup.bat
```

### 2. Configure Environment

Update `.env` with your OpenAI API key:

```env
OPENAI_API_KEY=sk-your-actual-openai-key-here
```

### 3. Start Services

```bash
docker-compose up -d
```

### 4. Access Services

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **n8n**: http://localhost:5678 (admin/admin)
- **pgAdmin**: http://localhost:5050 (admin@admin.com/admin)

### 5. Import n8n Workflow

1. Access n8n at http://localhost:5678
2. Login with admin/admin
3. Import `workflows/resume-analyzer-workflow.json`
4. Configure OpenAI credentials
5. Activate the workflow

## 🔧 API Endpoints

### Authentication
```bash
# Login
POST /auth/login
{
  "username": "admin",
  "password": "admin123"
}

# Register new user
POST /auth/register
{
  "username": "newuser",
  "email": "user@example.com",
  "password": "password123"
}

# Get current user
GET /auth/me
Authorization: Bearer <token>
```

### Resume Management
```bash
# Upload resume
POST /api/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data
file: resume.pdf

# Get all resumes
GET /resumes?skip=0&limit=10
Authorization: Bearer <token>

# Get specific resume
GET /resumes/{resume_id}
Authorization: Bearer <token>

# Check upload status
GET /api/upload/status/{resume_id}
Authorization: Bearer <token>
```

## 🧪 Testing

### API Testing
```bash
# Run API tests
chmod +x test-api.sh
./test-api.sh
```

### Manual Testing
```bash
# Get access token
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | jq -r '.access_token')

# Upload a resume
curl -X POST http://localhost:8000/api/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@sample-resume.pdf"

# Check results
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/resumes
```

## 📊 Database Schema

### `resumes` table
```sql
CREATE TABLE resumes (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    skills TEXT[],
    experience_years INTEGER,
    last_job_title VARCHAR(255),
    raw_text TEXT,
    analysis_status VARCHAR(50) DEFAULT 'pending',
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 🔄 Workflow Process

1. **Upload**: User uploads PDF via API
2. **Trigger**: n8n webhook receives file info
3. **Extract**: PDF text extraction using Tika
4. **Analyze**: OpenAI parses structured data
5. **Store**: Results saved to PostgreSQL
6. **Notify**: Backend updated with results

## 🛠️ Development

### Local Development
```bash
# Start only database
docker-compose up postgres -d

# Run FastAPI locally
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

## 🔍 Troubleshooting

### Common Issues

**1. JWT Authentication Fails**
```bash
# Check token format
curl -H "Authorization: Bearer <token>" http://localhost:8000/auth/me
```

**2. n8n Webhook Not Working**
- Verify webhook URL in environment
- Check n8n workflow is active
- Ensure OpenAI credentials are configured

**3. Database Connection Issues**
```bash
# Check database logs
docker-compose logs postgres
```

### Logs
```bash
# View all logs
docker-compose logs

# Specific service logs
docker-compose logs backend
```

## 📄 License

MIT License