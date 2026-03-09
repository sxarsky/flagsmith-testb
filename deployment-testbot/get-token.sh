#!/bin/bash
# TestBot Auth Token Script for Flagsmith
# Logs in and outputs API token

API_BASE="http://localhost:8080/api/v1"

TOKEN=$(curl -s -X POST "$API_BASE/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"TestPass123!"}' \
  | jq -r '.key')

echo "$TOKEN"
