#!/bin/bash
echo "Seeding UNSW Courses..."

# Course 1: COMP1511
curl -s -X POST http://127.0.0.1:5004/courses \
  -H "Content-Type: application/json" \
  -d '{
    "course_code": "COMP1511",
    "title": "Programming Fundamentals",
    "description": "Introduction to programming using C. Covers data types, control flow, functions, arrays, pointers, and memory management.",
    "department": "Computer Science",
    "instructor": "UNSW Faculty",
    "credits": 6,
    "level": "undergraduate",
    "semester": "Term 1",
    "tags": ["c", "programming", "fundamentals"],
    "prerequisites": []
  }' > /dev/null

# Course 2: MATH1131
curl -s -X POST http://127.0.0.1:5004/courses \
  -H "Content-Type: application/json" \
  -d '{
    "course_code": "MATH1131",
    "title": "Mathematics 1A",
    "description": "Complex numbers, vectors, matrices, systems of linear equations. Limits, continuity, differentiation, integration, Taylor series.",
    "department": "Mathematics",
    "instructor": "UNSW Faculty",
    "credits": 6,
    "level": "undergraduate",
    "semester": "Term 1",
    "tags": ["calculus", "algebra", "mathematics"],
    "prerequisites": []
  }' > /dev/null

# Course 3: PHYS1121
curl -s -X POST http://127.0.0.1:5004/courses \
  -H "Content-Type: application/json" \
  -d '{
    "course_code": "PHYS1121",
    "title": "Physics 1A",
    "description": "Mechanics, thermal physics, waves and optics. An introduction to fundamental physical principles and problem solving.",
    "department": "Physics",
    "instructor": "UNSW Faculty",
    "credits": 6,
    "level": "undergraduate",
    "semester": "Term 1",
    "tags": ["physics", "mechanics", "science"],
    "prerequisites": []
  }' > /dev/null

# Course 4: INFS1602
curl -s -X POST http://127.0.0.1:5004/courses \
  -H "Content-Type: application/json" \
  -d '{
    "course_code": "INFS1602",
    "title": "Digital Transformation in Business",
    "description": "Explore how digital technologies are transforming business models, operations, and customer experiences in modern organizations.",
    "department": "Information Systems",
    "instructor": "UNSW Faculty",
    "credits": 6,
    "level": "undergraduate",
    "semester": "Term 2",
    "tags": ["business", "digital", "transformation", "IT"],
    "prerequisites": []
  }' > /dev/null

# Course 5: PSYC1001
curl -s -X POST http://127.0.0.1:5004/courses \
  -H "Content-Type: application/json" \
  -d '{
    "course_code": "PSYC1001",
    "title": "Psychology 1A",
    "description": "Introduction to the scientific study of human behavior and mental processes. Covers biological bases, perception, learning, and cognition.",
    "department": "Psychology",
    "instructor": "UNSW Faculty",
    "credits": 6,
    "level": "undergraduate",
    "semester": "Term 1",
    "tags": ["psychology", "mind", "behavior", "science"],
    "prerequisites": []
  }' > /dev/null

# Course 6: ECON1101
curl -s -X POST http://127.0.0.1:5004/courses \
  -H "Content-Type: application/json" \
  -d '{
    "course_code": "ECON1101",
    "title": "Microeconomics 1",
    "description": "Analysis of the behavior of individual consumers and firms. Supply and demand, market structures, and public policy implications.",
    "department": "Economics",
    "instructor": "UNSW Faculty",
    "credits": 6,
    "level": "undergraduate",
    "semester": "Term 1",
    "tags": ["economics", "microeconomics", "business", "markets"],
    "prerequisites": []
  }' > /dev/null

# Course 7: ARTS1090
curl -s -X POST http://127.0.0.1:5004/courses \
  -H "Content-Type: application/json" \
  -d '{
    "course_code": "ARTS1090",
    "title": "Media, Culture and Everyday Life",
    "description": "Introduction to media studies. Explores the role of media in shaping contemporary culture, society, and identity.",
    "department": "Media and Communications",
    "instructor": "UNSW Faculty",
    "credits": 6,
    "level": "undergraduate",
    "semester": "Term 1",
    "tags": ["media", "culture", "arts", "communications"],
    "prerequisites": []
  }' > /dev/null

# Course 8: ENGG1000
curl -s -X POST http://127.0.0.1:5004/courses \
  -H "Content-Type: application/json" \
  -d '{
    "course_code": "ENGG1000",
    "title": "Introduction to Engineering Design",
    "description": "Hands-on project based course introducing engineering design principles, teamwork, and problem solving across various disciplines.",
    "department": "Engineering",
    "instructor": "UNSW Faculty",
    "credits": 6,
    "level": "undergraduate",
    "semester": "Term 1",
    "tags": ["engineering", "design", "projects", "teamwork"],
    "prerequisites": []
  }' > /dev/null

# Course 9: LAWS1052
curl -s -X POST http://127.0.0.1:5004/courses \
  -H "Content-Type: application/json" \
  -d '{
    "course_code": "LAWS1052",
    "title": "Introducing Law and Justice",
    "description": "Foundational course exploring the Australian legal system, principles of law, statutory interpretation, and concepts of justice.",
    "department": "Law",
    "instructor": "UNSW Faculty",
    "credits": 6,
    "level": "undergraduate",
    "semester": "Term 1",
    "tags": ["law", "justice", "legal system"],
    "prerequisites": []
  }' > /dev/null

# Course 10: BABS1201
curl -s -X POST http://127.0.0.1:5004/courses \
  -H "Content-Type: application/json" \
  -d '{
    "course_code": "BABS1201",
    "title": "Molecules, Cells and Genes",
    "description": "Introduction to molecular and cellular biology. Covers DNA, genetics, cell structure, metabolism, and biotechnology concepts.",
    "department": "Biological Sciences",
    "instructor": "UNSW Faculty",
    "credits": 6,
    "level": "undergraduate",
    "semester": "Term 1",
    "tags": ["biology", "genetics", "cells", "science"],
    "prerequisites": []
  }' > /dev/null

# Course 11: COMP2521
curl -s -X POST http://127.0.0.1:5004/courses \
  -H "Content-Type: application/json" \
  -d '{
    "course_code": "COMP2521",
    "title": "Data Structures and Algorithms",
    "description": "Advanced programming covering linked lists, trees, graphs, sorting, and algorithm analysis to write efficient software.",
    "department": "Computer Science",
    "instructor": "UNSW Faculty",
    "credits": 6,
    "level": "undergraduate",
    "semester": "Term 2",
    "tags": ["algorithms", "c", "data structures", "software engineering"],
    "prerequisites": ["COMP1511"]
  }' > /dev/null

# Course 12: MARK1012
curl -s -X POST http://127.0.0.1:5004/courses \
  -H "Content-Type: application/json" \
  -d '{
    "course_code": "MARK1012",
    "title": "Marketing Fundamentals",
    "description": "Core principles of marketing, consumer behavior, market research, and strategic marketing planning for products and services.",
    "department": "Marketing",
    "instructor": "UNSW Faculty",
    "credits": 6,
    "level": "undergraduate",
    "semester": "Term 2",
    "tags": ["marketing", "business", "commerce", "strategy"],
    "prerequisites": []
  }' > /dev/null

echo "Courses inserted successfully (or already exist)!"
