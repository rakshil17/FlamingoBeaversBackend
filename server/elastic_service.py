from __future__ import annotations

from elasticsearch import Elasticsearch, NotFoundError

from config import settings


STARTUP_COURSE = {
    "course_code": "CS101",
    "title": "Introduction to Programming",
    "description": (
        "Foundational programming course covering variables, control "
        "flow, functions, debugging, and problem solving with Python."
    ),
    "department": "Computer Science",
    "instructor": "Dr. Ada Mensah",
    "credits": 3,
    "level": "undergraduate",
    "semester": "Fall 2026",
    "tags": ["programming", "python", "fundamentals"],
    "prerequisites": [],
    "course_fee": 1200.00,
}


INDEX_MAPPINGS = {
    "properties": {
        "course_code": {"type": "keyword"},
        "title": {"type": "text"},
        "description": {"type": "text"},
        "department": {"type": "keyword"},
        "instructor": {"type": "text"},
        "credits": {"type": "integer"},
        "level": {"type": "keyword"},
        "semester": {"type": "keyword"},
        "tags": {"type": "keyword"},
        "prerequisites": {"type": "keyword"},
        "course_fee": {"type": "float"},
        "semantic_text": {"type": "text"},
        "text_embedding": {
            "properties": {
                "predicted_value": {"type": "sparse_vector"}
            }
        }
    }
}


DEGREE_INDEX_MAPPINGS = {
    "properties": {
        "degree_id": {"type": "keyword"},
        "name": {"type": "text"},
        "faculty": {"type": "keyword"},
        "school": {"type": "keyword"},
        "total_uoc": {"type": "integer"},
        "duration_years": {"type": "float"},
        "delivery_mode": {"type": "keyword"},
        "level": {"type": "keyword"},
        "description": {"type": "text"},
        "specialisations": {
            "type": "nested",
            "properties": {
                "name": {"type": "text"},
                "required_uoc": {"type": "integer"},
                "courses": {"type": "keyword"},
            },
        },
        "requirements": {
            "properties": {
                "type": {"type": "keyword"},
                "rules": {
                    "type": "nested",
                    "properties": {
                        "type": {"type": "keyword"},
                        "label": {"type": "text"},
                        "uoc": {"type": "integer"},
                        "courses": {"type": "keyword"},
                        "lists": {"type": "keyword"},
                        "tags": {"type": "keyword"},
                    },
                },
            }
        },
    }
}


SAMPLE_DEGREE = {
    "degree_id": "COMPSC3001",
    "name": "Bachelor of Computer Science",
    "faculty": "Engineering",
    "school": "Computer Science and Engineering",
    "total_uoc": 144,
    "duration_years": 3,
    "delivery_mode": "in-person",
    "level": "undergraduate",
    "description": (
        "UNSW Computer Science degree with core, electives, and "
        "gen ed requirements."
    ),
    "specialisations": [
        {
            "name": "Artificial Intelligence",
            "required_uoc": 36,
            "courses": ["COMP3411", "COMP4418"],
        }
    ],
    "requirements": {
        "type": "AllOf",
        "rules": [
            {
                "type": "MinUOC",
                "label": "Core Courses",
                "uoc": 66,
                "courses": ["COMP1511", "COMP1521", "COMP2521"],
            },
            {
                "type": "MinUOC",
                "label": "Disciplinary Electives",
                "uoc": 30,
                "lists": ["COMP3###", "COMP4###"],
            },
            {
                "type": "MinUOC",
                "label": "General Education",
                "uoc": 12,
                "tags": ["gen_ed"],
            },
            {
                "type": "FreeElectives",
                "uoc": 18,
            },
        ],
    },
}


def create_client() -> Elasticsearch:
    kwargs: dict = {}
    if settings.elastic_api_key:
        kwargs["api_key"] = settings.elastic_api_key
    return Elasticsearch(settings.elastic_host, **kwargs)


client = create_client()


def _as_dict(response: object) -> dict:
    body = getattr(response, "body", response)
    return body if isinstance(body, dict) else {"response": body}


def ensure_index_exists() -> dict:
    # Attempt to create the ingest pipeline first
    pipeline_id = "elser-v2-pipeline"
    try:
        client.ingest.put_pipeline(
            id=pipeline_id,
            body={
                "description": "ELSER v2 pipeline for course descriptions",
                "processors": [
                    {
                        "inference": {
                            "model_id": "my-elser-model",
                            "field_map": {
                                "semantic_text": "text_field"
                            },
                            "target_field": "text_embedding"
                        }
                    }
                ]
            }
        )
    except Exception as e:
        print(f"Warning: Failed to create or update ELSER pipeline: {e}")

    if client.indices.exists(index=settings.elastic_index):
        return {"index": settings.elastic_index, "created": False}

    create_response = client.indices.create(
        index=settings.elastic_index,
        body={
            "settings": {
                "default_pipeline": pipeline_id
            }
        }
    )
    mapping_response = client.indices.put_mapping(
        index=settings.elastic_index,
        body=INDEX_MAPPINGS,
    )
    return {
        "index": settings.elastic_index,
        "created": True,
        "create": _as_dict(create_response),
        "mapping": _as_dict(mapping_response),
    }


def add_course(course: dict) -> dict:
    course_code = str(course.get("course_code", "")).strip()
    if not course_code:
        raise ValueError("'course_code' is required in course payload.")

    ensure_index_exists()

    if client.exists(index=settings.elastic_index, id=course_code):
        return {
            "result": "already_exists",
            "id": course_code,
            "index": settings.elastic_index,
        }

    # Prepare semantic text for ELSER
    title = course.get("title", "")
    desc = course.get("description", "")
    tags = " ".join(course.get("tags", []))
    course["semantic_text"] = f"{title} {desc} {tags}".strip()

    response = client.index(
        index=settings.elastic_index,
        id=course_code,
        document=course,
        refresh="wait_for",
    )
    return {
        "result": response.get("result"),
        "id": response.get("_id"),
        "index": response.get("_index"),
    }


def get_course(course_code: str) -> dict:
    response = client.get(index=settings.elastic_index, id=course_code)
    return {
        "id": response.get("_id"),
        "index": response.get("_index"),
        "course": response.get("_source", {}),
    }


def delete_course(course_code: str) -> dict:
    response = client.delete(
        index=settings.elastic_index,
        id=course_code,
        refresh="wait_for",
    )
    return {
        "result": response.get("result"),
        "id": response.get("_id"),
        "index": response.get("_index"),
    }


def clear_courses() -> dict:
    if not client.indices.exists(index=settings.elastic_index):
        return {
            "index": settings.elastic_index,
            "deleted": 0,
            "message": "Index does not exist.",
        }

    response = client.delete_by_query(
        index=settings.elastic_index,
        query={"match_all": {}},
        refresh=True,
        conflicts="proceed",
    )
    return {
        "index": settings.elastic_index,
        "deleted": response.get("deleted", 0),
        "total": response.get("total", 0),
    }


def seed_startup_course() -> dict:
    result = add_course(dict(STARTUP_COURSE))
    return {
        "seeded": True,
        "course_code": STARTUP_COURSE["course_code"],
        "result": result.get("result"),
    }


def ensure_degree_index_exists() -> dict:
    if client.indices.exists(index=settings.elastic_degree_index):
        return {"index": settings.elastic_degree_index, "created": False}

    create_response = client.indices.create(
        index=settings.elastic_degree_index
    )
    mapping_response = client.indices.put_mapping(
        index=settings.elastic_degree_index,
        body=DEGREE_INDEX_MAPPINGS,
    )
    return {
        "index": settings.elastic_degree_index,
        "created": True,
        "create": _as_dict(create_response),
        "mapping": _as_dict(mapping_response),
    }


def add_degree(degree: dict) -> dict:
    degree_id = str(degree.get("degree_id", "")).strip()
    if not degree_id:
        raise ValueError("'degree_id' is required in degree payload.")

    ensure_degree_index_exists()
    response = client.index(
        index=settings.elastic_degree_index,
        id=degree_id,
        document=degree,
        refresh="wait_for",
    )
    return {
        "result": response.get("result"),
        "id": response.get("_id"),
        "index": response.get("_index"),
    }


def get_degree(degree_id: str) -> dict:
    response = client.get(index=settings.elastic_degree_index, id=degree_id)
    return {
        "id": response.get("_id"),
        "index": response.get("_index"),
        "degree": response.get("_source", {}),
    }


def clear_degrees() -> dict:
    if not client.indices.exists(index=settings.elastic_degree_index):
        return {
            "index": settings.elastic_degree_index,
            "deleted": 0,
            "message": "Index does not exist.",
        }

    response = client.delete_by_query(
        index=settings.elastic_degree_index,
        query={"match_all": {}},
        refresh=True,
        conflicts="proceed",
    )
    return {
        "index": settings.elastic_degree_index,
        "deleted": response.get("deleted", 0),
        "total": response.get("total", 0),
    }


def seed_sample_degree() -> dict:
    result = add_degree(dict(SAMPLE_DEGREE))
    return {
        "seeded": True,
        "degree_id": SAMPLE_DEGREE["degree_id"],
        "result": result.get("result"),
    }


def generate_degree_plan(
    degree: str,
    subjects_per_term: int,
    career_goal: str,
    target_companies: str
) -> dict:
    ensure_index_exists()

    # We want at least enough courses for a basic degree, say 24 courses
    total_courses_needed = 24

    # Construct a natural language query for ELSER
    semantic_query = (
        f"I am studying {degree} and I want to become a {career_goal} "
        f"working at {target_companies}."
    ).strip()

    # Build a sparse_vector query targeting the ELSER embeddings
    query = {
        "size": total_courses_needed,
        "query": {
            "sparse_vector": {
                "field": "text_embedding.predicted_value",
                "inference_id": "my-elser-model",
                "query": semantic_query
            }
        }
    }

    # Execute the search
    response = client.search(index=settings.elastic_index, body=query)
    hits = response.get("hits", {}).get("hits", [])

    # Extract just the course data
    courses = [hit.get("_source", {}) for hit in hits]

    if not courses:
        return {
            "recommended_plan": [],
            "cheapest_plan": [],
            "message": "No courses found matching your criteria."
        }

    # Logic to chunk courses into terms
    def chunk_into_terms(course_list, n):
        terms = []
        for i in range(0, len(course_list), n):
            terms.append({
                "term_number": (i // n) + 1,
                "courses": course_list[i:i + n]
            })
        return terms

    # Recommended plan: based directly on search relevance.
    recommended_plan = chunk_into_terms(courses, subjects_per_term)

    # Cheapest plan: sort courses by course_fee (ascending)
    # Courses with no fee are sent to the end.
    cheapest_courses = sorted(
        courses,
        key=lambda c: c.get("course_fee", 999999),
    )
    cheapest_plan = chunk_into_terms(cheapest_courses, subjects_per_term)

    return {
        "recommended_plan": recommended_plan,
        "cheapest_plan": cheapest_plan,
    }


__all__ = [
    "NotFoundError",
    "add_course",
    "add_degree",
    "clear_courses",
    "clear_degrees",
    "client",
    "delete_course",
    "ensure_degree_index_exists",
    "generate_degree_plan",
    "get_degree",
    "get_course",
    "seed_sample_degree",
    "seed_startup_course",
]
