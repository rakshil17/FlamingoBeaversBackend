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
    }
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
    if client.indices.exists(index=settings.elastic_index):
        return {"index": settings.elastic_index, "created": False}

    create_response = client.indices.create(index=settings.elastic_index)
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


__all__ = [
    "NotFoundError",
    "add_course",
    "clear_courses",
    "client",
    "delete_course",
    "get_course",
    "seed_startup_course",
]
