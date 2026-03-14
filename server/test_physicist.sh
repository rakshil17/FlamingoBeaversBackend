#!/bin/bash
curl -s -X POST http://127.0.0.1:5004/agent/plan \
  -H "Content-Type: application/json" \
  -d '{
    "degree": "Bachelors of Science (Physics)",
    "subjects_per_term": 2,
    "career_goal": "Physicist",
    "target_companies": "NASA"
  }' | jq
