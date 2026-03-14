#!/bin/bash

# Test 1: Standard Software Engineering
echo "Test 1: Software Engineer"
curl -s -X POST http://127.0.0.1:5002/agent/plan \
  -H "Content-Type: application/json" \
  -d '{
    "degree": "Bachelors of Computer Science",
    "subjects_per_term": 2,
    "career_goal": "Software Engineer",
    "target_companies": "Google"
  }' | jq

echo -e "\n----------------------------------------\n"

# Test 2: Database Engineer Request
echo "Test 2: Database Engineer"
curl -s -X POST http://127.0.0.1:5002/agent/plan \
  -H "Content-Type: application/json" \
  -d '{
    "degree": "Bachelors of IT",
    "subjects_per_term": 2,
    "career_goal": "Database Engineer",
    "target_companies": "Oracle"
  }' | jq

echo -e "\n----------------------------------------\n"

# Test 3: Abstract request
echo "Test 3: Abstract Request"
curl -s -X POST http://127.0.0.1:5002/agent/plan \
  -H "Content-Type: application/json" \
  -d '{
    "degree": "Undecided Undergrad",
    "subjects_per_term": 1,
    "career_goal": "I want to invent new puzzle games that challenge the mind using fast code",
    "target_companies": "Nintendo"
  }' | jq
