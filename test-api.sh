#!/bin/bash

BASE_URL="http://localhost:8000"
echo "🧪 Testing Resume Analyzer API..."

# Test health endpoint
echo "1. Testing health endpoint..."
curl -s $BASE_URL/health | jq '.' || echo "❌ Health check failed"

# Test login
echo -e "\n2. Testing login..."
TOKEN=$(curl -s -X POST $BASE_URL/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | jq -r '.access_token')

if [ "$TOKEN" != "null" ] && [ "$TOKEN" != "" ]; then
    echo "✅ Login successful"
    echo "Token: $TOKEN"
else
    echo "❌ Login failed"
    exit 1
fi

# Test protected endpoint
echo -e "\n3. Testing protected endpoint..."
curl -s -H "Authorization: Bearer $TOKEN" $BASE_URL/resumes | jq '.' || echo "❌ Protected endpoint failed"

# Test user info
echo -e "\n4. Testing user info..."
curl -s -H "Authorization: Bearer $TOKEN" $BASE_URL/auth/me | jq '.' || echo "❌ User info failed"

echo -e "\n✅ API tests completed!"
echo -e "\n📝 To test file upload, use:"
echo "curl -X POST $BASE_URL/api/upload \\"
echo "  -H 'Authorization: Bearer $TOKEN' \\"
echo "  -F 'file=@path/to/your/resume.pdf'"
