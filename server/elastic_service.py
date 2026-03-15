from __future__ import annotations

from elasticsearch import Elasticsearch, NotFoundError

from config import settings


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
        "enrolment_rules": {"type": "text"},
        "fees": {
            "properties": {
                "domestic": {"type": "keyword"},
                "international": {"type": "keyword"},
                "hecs": {"type": "keyword"},
            }
        },
        # Backward compatibility with older docs.
        "course_fee": {"type": "float"},
        "semantic_text": {"type": "text"},
        "text_embedding": {
            "properties": {
                "predicted_value": {"type": "sparse_vector"},
                "model_id": {"type": "keyword"},
            }
        },
    }
}


DEGREE_INDEX_MAPPINGS = {
    "properties": {
        "degree_id": {"type": "keyword"},
        "degree_name": {"type": "text"},
        "program_code": {"type": "keyword"},
        "specialisation_code": {"type": "keyword"},
        "faculty": {"type": "keyword"},
        "school": {"type": "keyword"},
        "total_uoc": {"type": "integer"},
        "duration_years": {"type": "float"},
        "level": {"type": "keyword"},
        "core_courses": {
            "type": "nested",
            "properties": {
                "course_code": {"type": "keyword"},
                "uoc": {"type": "integer"},
                "title": {"type": "text"},
            },
        },
        "core_uoc": {"type": "integer"},
        "thesis": {
            "properties": {
                "label": {"type": "text"},
                "uoc": {"type": "integer"},
                "courses": {
                    "type": "nested",
                    "properties": {
                        "course_code": {"type": "keyword"},
                        "uoc": {"type": "integer"},
                        "title": {"type": "text"},
                    },
                },
            },
        },
        "remaining_elective_uoc": {"type": "integer"},
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
                            "field_map": {"semantic_text": "text_field"},
                            "target_field": "text_embedding",
                        }
                    }
                ],
            },
        )
    except Exception:
        # Keep app resilient if pipeline setup is temporarily unavailable.
        pass

    if client.indices.exists(index=settings.elastic_index):
        mapping_response = client.indices.put_mapping(
            index=settings.elastic_index,
            body=INDEX_MAPPINGS,
        )
        return {
            "index": settings.elastic_index,
            "created": False,
            "mapping": _as_dict(mapping_response),
        }

    create_response = client.indices.create(
        index=settings.elastic_index,
        body={"settings": {"default_pipeline": pipeline_id}},
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

    title = course.get("title", "")
    description = course.get("description", "")
    tags = " ".join(course.get("tags", []))
    course["semantic_text"] = f"{title} {description} {tags}".strip()

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


def ensure_degree_index_exists() -> dict:
    if client.indices.exists(index=settings.elastic_degree_index):
        mapping_response = client.indices.put_mapping(
            index=settings.elastic_degree_index,
            body=DEGREE_INDEX_MAPPINGS,
        )
        return {
            "index": settings.elastic_degree_index,
            "created": False,
            "mapping": _as_dict(mapping_response),
        }

    create_response = client.indices.create(index=settings.elastic_degree_index)
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


def delete_degree(degree_id: str) -> dict:
    response = client.delete(
        index=settings.elastic_degree_index,
        id=degree_id,
        refresh="wait_for",
    )
    return {
        "result": response.get("result"),
        "id": response.get("_id"),
        "index": response.get("_index"),
    }


__all__ = [
    "NotFoundError",
    "add_course",
    "add_degree",
    "clear_degrees",
    "client",
    "delete_degree",
    "ensure_degree_index_exists",
    "get_degree",
    "get_course",
]
