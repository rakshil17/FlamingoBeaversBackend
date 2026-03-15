from flask import Flask, request

from config import settings
from elastic_service import (
    NotFoundError,
    add_course,
    add_degree,
    client,
    delete_degree,
    ensure_degree_index_exists,
    get_degree,
    get_course,
    clear_degrees,
)
from planning_service import (
    DEFAULT_DEGREE_ID,
    DEFAULT_ENROLLMENT_YEAR,
    DEFAULT_START_TERM,
    FEE_PLAN_OPTIONS,
    build_plan,
    list_degree_options,
    normalize_existing_plan,
    suggest_manual_course_for_slot,
    validate_manual_course_add,
)


app = Flask(__name__)


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    return response

# In-memory fee plan selection (hecs / domestic / international).
fee_plan_state: dict = {"fee_type": "hecs"}

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


@app.get("/planning/fee-plan")
def get_fee_plan() -> tuple[dict, int]:
    return {"fee_type": fee_plan_state["fee_type"]}, 200


@app.post("/planning/fee-plan")
def set_fee_plan() -> tuple[dict, int]:
    payload = request.get_json(silent=True) or {}
    fee_type = str(payload.get("fee_type", "")).strip().lower()
    if fee_type not in FEE_PLAN_OPTIONS:
        return {
            "error": f"'fee_type' must be one of: {sorted(FEE_PLAN_OPTIONS)}"
        }, 400
    fee_plan_state["fee_type"] = fee_type
    return {"fee_type": fee_type, "message": "Fee plan updated."}, 200


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


@app.get("/degrees/options")
def degree_options() -> tuple[dict, int]:
    try:
        options = list_degree_options()
    except Exception as exc:
        return {"error": f"Failed to list degrees: {exc}"}, 500

    return {"degrees": options}, 200


@app.post("/planning/cheapest")
def planning_cheapest() -> tuple[dict, int]:
    payload = request.get_json(silent=True) or {}
    fee_type = str(payload.get("fee_type", fee_plan_state["fee_type"])).strip().lower()
    if fee_type not in FEE_PLAN_OPTIONS:
        return {
            "error": f"'fee_type' must be one of: {sorted(FEE_PLAN_OPTIONS)}"
        }, 400
    fee_plan_state["fee_type"] = fee_type

    try:
        result = build_plan(
            degree_id=DEFAULT_DEGREE_ID,
            mode="cheapest",
            fee_type=fee_type,
        )
    except Exception as exc:
        return {"error": f"Failed to build cheapest plan: {exc}"}, 500

    return result, 200


@app.post("/planning/easiest")
def planning_easiest() -> tuple[dict, int]:
    payload = request.get_json(silent=True) or {}
    fee_type = str(payload.get("fee_type", fee_plan_state["fee_type"])).strip().lower()
    if fee_type not in FEE_PLAN_OPTIONS:
        return {
            "error": f"'fee_type' must be one of: {sorted(FEE_PLAN_OPTIONS)}"
        }, 400
    fee_plan_state["fee_type"] = fee_type

    try:
        result = build_plan(
            degree_id=DEFAULT_DEGREE_ID,
            mode="easiest",
            fee_type=fee_type,
        )
    except Exception as exc:
        return {"error": f"Failed to build easiest plan: {exc}"}, 500

    return result, 200


@app.post("/planning/recommended")
def planning_recommended() -> tuple[dict, int]:
    payload = request.get_json(silent=True) or {}
    career_goal = str(payload.get("career_goal", "")).strip()
    fee_type = str(payload.get("fee_type", fee_plan_state["fee_type"])).strip().lower()

    if fee_type not in FEE_PLAN_OPTIONS:
        return {
            "error": f"'fee_type' must be one of: {sorted(FEE_PLAN_OPTIONS)}"
        }, 400
    fee_plan_state["fee_type"] = fee_type

    if not career_goal:
        return {"error": "'career_goal' is required."}, 400

    try:
        result = build_plan(
            degree_id=DEFAULT_DEGREE_ID,
            mode="recommended",
            job_interest_query=career_goal,
            fee_type=fee_type,
        )
    except Exception as exc:
        return {"error": f"Failed to build recommended plan: {exc}"}, 500

    return result, 200


@app.post("/planning")
@app.post("/api/planning")
def planning() -> tuple[dict, int]:
    payload = request.get_json(silent=True) or {}

    mode = str(payload.get("mode", "recommended")).strip().lower()
    if mode not in {"recommended", "cheapest", "easiest"}:
        return {
            "error": "'mode' must be one of: ['cheapest', 'easiest', 'recommended']"
        }, 400

    fee_type = str(payload.get("fee_type", fee_plan_state["fee_type"])).strip().lower()
    if fee_type not in FEE_PLAN_OPTIONS:
        return {
            "error": f"'fee_type' must be one of: {sorted(FEE_PLAN_OPTIONS)}"
        }, 400
    fee_plan_state["fee_type"] = fee_type

    if mode == "recommended":
        career_goal = str(payload.get("career_goal", "")).strip()
        if not career_goal:
            return {"error": "'career_goal' is required for recommended mode."}, 400
        try:
            result = build_plan(
                degree_id=DEFAULT_DEGREE_ID,
                mode="recommended",
                job_interest_query=career_goal,
                fee_type=fee_type,
            )
        except Exception as exc:
            return {"error": f"Failed to build recommended plan: {exc}"}, 500
        return result, 200

    if mode == "cheapest":
        try:
            result = build_plan(
                degree_id=DEFAULT_DEGREE_ID,
                mode="cheapest",
                fee_type=fee_type,
            )
        except Exception as exc:
            return {"error": f"Failed to build cheapest plan: {exc}"}, 500
        return result, 200

    try:
        result = build_plan(
            degree_id=DEFAULT_DEGREE_ID,
            mode="easiest",
            fee_type=fee_type,
        )
    except Exception as exc:
        return {"error": f"Failed to build easiest plan: {exc}"}, 500

    return result, 200


@app.post("/planning/context")
def planning_context() -> tuple[dict, int]:
    return {
        "degree_id": DEFAULT_DEGREE_ID,
        "enrollment_year": DEFAULT_ENROLLMENT_YEAR,
        "start_term": DEFAULT_START_TERM,
        "fee_type": fee_plan_state["fee_type"],
        "completed_courses": [],
        "terms_per_year": 3,
        "message": "Planning context accepted (fresh start assumptions).",
    }, 200


@app.post("/planning/manual-add")
def planning_manual_add() -> tuple[dict, int]:
    payload = request.get_json(silent=True) or {}

    existing_plan_terms = normalize_existing_plan(
        payload.get("existing_plan_terms", [])
    )
    target_year = payload.get("target_year")
    target_term = str(payload.get("target_term", "")).strip()
    course_code = str(payload.get("course_code", "")).strip()
    course_query = str(payload.get("course_query", "")).strip()

    if not all([target_year, target_term]):
        return {
            "error": "'target_year' and 'target_term' are required."
        }, 400

    if not course_code and not course_query:
        return {
            "error": "Provide either 'course_code' or 'course_query'."
        }, 400

    try:
        target_year_value = int(str(target_year))
        if course_code:
            result = validate_manual_course_add(
                degree_id=DEFAULT_DEGREE_ID,
                existing_plan_terms=existing_plan_terms,
                target_year=target_year_value,
                target_term=target_term,
                course_code=course_code,
                enrollment_year=DEFAULT_ENROLLMENT_YEAR,
                completed_courses=[],
            )
        else:
            result = suggest_manual_course_for_slot(
                degree_id=DEFAULT_DEGREE_ID,
                existing_plan_terms=existing_plan_terms,
                target_year=target_year_value,
                target_term=target_term,
                course_query=course_query,
                enrollment_year=DEFAULT_ENROLLMENT_YEAR,
                completed_courses=[],
            )
    except ValueError:
        return {"error": "'target_year' must be a number."}, 400
    except Exception as exc:
        return {"error": f"Failed manual course validation: {exc}"}, 500

    return result, 200 if result.get("valid") else 400


@app.post("/degrees/setup")
def setup_degree_index() -> tuple[dict, int]:
    try:
        result = ensure_degree_index_exists()
    except Exception as exc:
        return {"error": f"Failed to setup degree index: {exc}"}, 500

    return result, 200


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


@app.delete("/degrees/<degree_id>")
def remove_degree(degree_id: str) -> tuple[dict, int]:
    try:
        result = delete_degree(degree_id)
    except NotFoundError:
        return {"error": "Degree not found."}, 404
    except Exception as exc:
        return {"error": f"Failed to delete degree: {exc}"}, 500

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
