from flask import Flask, request

from config import settings
from elastic_service import (
    NotFoundError,
    add_course,
    clear_courses,
    client,
    delete_course,
    get_course,
    seed_startup_course,
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


@app.get("/")
def root() -> tuple[dict, int]:
    return {
        "service": "flamingo-beavers-backend",
        "status": "ok",
        "index": settings.elastic_index,
        "startup_seed": startup_seed_status,
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


if __name__ == "__main__":
    app.run(
        host=settings.flask_host,
        port=settings.flask_port,
        debug=settings.flask_debug,
    )
