from flask import Flask, request

from config import settings
from elastic_service import (
    NotFoundError,
    add_course,
    add_degree,
    clear_courses,
    clear_degrees,
    client,
    delete_course,
    ensure_degree_index_exists,
    get_degree,
    get_course,
    seed_startup_course,
    seed_sample_degree,
    generate_degree_plan,
)


app = Flask(__name__)
startup_seed_status = {
    "attempted": False,
    "seeded": False,
}

try:
    startup_seed_status = {
        "attempted": True,
        **seed_startup_course(),
    }
except Exception as exc:  # pragma: no cover - startup should not crash API
    startup_seed_status = {
        "attempted": True,
        "seeded": False,
        "error": str(exc),
    }

degree_index_status = {
    "attempted": False,
    "created": False,
}

try:
    degree_index_status = {
        "attempted": True,
        **ensure_degree_index_exists(),
    }
except Exception as exc:
    degree_index_status = {
        "attempted": True,
        "created": False,
        "error": str(exc),
    }


@app.get("/")
def root() -> tuple[dict, int]:
    return {
        "service": "flamingo-beavers-backend",
        "status": "ok",
        "index": settings.elastic_index,
        "degree_index": settings.elastic_degree_index,
        "startup_seed": startup_seed_status,
        "degree_index_status": degree_index_status,
    }, 200


@app.get("/health")
def health() -> tuple[dict, int]:
    try:
        elastic_ok = bool(client.ping())
        info = client.info() if elastic_ok else {}
    except Exception as exc:  # pragma: no cover - best effort health signal
        return {
            "status": "degraded",
            "elasticsearch": False,
            "error": str(exc),
        }, 503

    return {
        "status": "ok" if elastic_ok else "degraded",
        "elasticsearch": elastic_ok,
        "cluster": info.get("cluster_name"),
        "version": info.get("version", {}).get("number"),
    }, 200 if elastic_ok else 503


@app.post("/courses")
def create_course() -> tuple[dict, int]:
    payload = request.get_json(silent=True) or {}

    if not isinstance(payload, dict):
        return {"error": "Payload must be a JSON object."}, 400

    try:
        result = add_course(payload)
    except ValueError as exc:
        return {"error": str(exc)}, 400
    except Exception as exc:
        return {"error": f"Failed to add course: {exc}"}, 500

    return result, 201


@app.get("/courses/<course_code>")
def read_course(course_code: str) -> tuple[dict, int]:
    try:
        result = get_course(course_code)
    except NotFoundError:
        return {"error": "Course not found."}, 404
    except Exception as exc:
        return {"error": f"Failed to fetch course: {exc}"}, 500

    return result, 200


@app.delete("/courses/<course_code>")
def remove_course(course_code: str) -> tuple[dict, int]:
    try:
        result = delete_course(course_code)
    except NotFoundError:
        return {"error": "Course not found."}, 404
    except Exception as exc:
        return {"error": f"Failed to delete course: {exc}"}, 500

    return result, 200


@app.delete("/courses")
def clear_course_database() -> tuple[dict, int]:
    try:
        result = clear_courses()
    except Exception as exc:
        return {"error": f"Failed to clear courses index: {exc}"}, 500

    return result, 200


@app.post("/agent/plan")
def get_degree_plan() -> tuple[dict, int]:
    payload = request.get_json(silent=True) or {}

    degree = payload.get("degree", "")
    subjects_per_term = payload.get("subjects_per_term", 3)
    career_goal = payload.get("career_goal", "")
    target_companies = payload.get("target_companies", "")

    if not degree or not career_goal:
        return {"error": "'degree' and 'career_goal' are required."}, 400

    try:
        if isinstance(subjects_per_term, str):
            subjects_per_term = int(subjects_per_term)
        # Fallback to 3 if somehow 0 or invalid
        if subjects_per_term <= 0:
            subjects_per_term = 3
    except ValueError:
        return {"error": "'subjects_per_term' must be a number."}, 400

    try:
        result = generate_degree_plan(
            degree=degree,
            subjects_per_term=subjects_per_term,
            career_goal=career_goal,
            target_companies=target_companies
        )
    except Exception as exc:
        return {"error": f"Failed to generate degree plan: {exc}"}, 500

    return result, 200


@app.post("/degrees/setup")
def setup_degree_index() -> tuple[dict, int]:
    try:
        result = ensure_degree_index_exists()
    except Exception as exc:
        return {"error": f"Failed to setup degree index: {exc}"}, 500

    return result, 200


@app.post("/degrees/seed")
def seed_degree_example() -> tuple[dict, int]:
    try:
        result = seed_sample_degree()
    except Exception as exc:
        return {"error": f"Failed to seed degree example: {exc}"}, 500

    return result, 201


@app.post("/degrees")
def create_degree() -> tuple[dict, int]:
    payload = request.get_json(silent=True) or {}

    if not isinstance(payload, dict):
        return {"error": "Payload must be a JSON object."}, 400

    try:
        result = add_degree(payload)
    except ValueError as exc:
        return {"error": str(exc)}, 400
    except Exception as exc:
        return {"error": f"Failed to add degree: {exc}"}, 500

    return result, 201


@app.get("/degrees/<degree_id>")
def read_degree(degree_id: str) -> tuple[dict, int]:
    try:
        result = get_degree(degree_id)
    except NotFoundError:
        return {"error": "Degree not found."}, 404
    except Exception as exc:
        return {"error": f"Failed to fetch degree: {exc}"}, 500

    return result, 200


@app.delete("/degrees")
def clear_degree_database() -> tuple[dict, int]:
    try:
        result = clear_degrees()
    except Exception as exc:
        return {"error": f"Failed to clear degrees index: {exc}"}, 500

    return result, 200


if __name__ == "__main__":
    app.run(
        host=settings.flask_host,
        port=settings.flask_port,
        debug=settings.flask_debug,
    )
