#!/bin/bash
set -e

# TestBot Setup Script for Flagsmith
# This script starts Flagsmith service and creates organization, project, and feature flags

cd "$(dirname "$0")"

# Clean up any existing containers and volumes
echo "Cleaning up existing containers..."
docker compose down -v 2>/dev/null || true

echo "Starting Flagsmith service..."
docker compose up -d

echo "Waiting for service to be ready..."
sleep 30

echo "Creating admin user..."
docker compose exec -T flagsmith python manage.py createsuperuser \
  --email "admin@example.com" \
  --noinput 2>/dev/null || true

# Set password
docker compose exec -T flagsmith python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
try:
    user = User.objects.get(email='admin@example.com')
    user.set_password('TestPass123!')
    user.save()
except: pass
EOF

echo "Logging in to get API key..."
API_BASE="http://localhost:8080/api/v1"
API_KEY=$(curl -s -X POST "$API_BASE/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"TestPass123!"}' \
  | jq -r '.key')

echo "Creating test data..."
# Create organization
ORG_ID=$(curl -s -X POST "$API_BASE/organisations/" \
  -H "Authorization: Token $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name":"TestBot Org"}' \
  | jq -r '.id' 2>/dev/null || echo "1")

# Create project
PROJECT_ID=$(curl -s -X POST "$API_BASE/projects/" \
  -H "Authorization: Token $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"TestBot Project\",\"organisation\":$ORG_ID}" \
  | jq -r '.id' 2>/dev/null || echo "1")

# Create feature flags
curl -s -X POST "$API_BASE/projects/$PROJECT_ID/features/" \
  -H "Authorization: Token $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name":"new_dashboard","type":"FLAG","description":"Enable new dashboard"}' > /dev/null 2>&1 || true

curl -s -X POST "$API_BASE/projects/$PROJECT_ID/features/" \
  -H "Authorization: Token $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name":"beta_features","type":"FLAG","description":"Enable beta features"}' > /dev/null 2>&1 || true

echo "✓ Flagsmith setup complete"
