from flask import Flask, request
from elasticsearch import Elasticsearch, NotFoundError

from server.config import settings


app = Flask(__name__)


def _create_es_client() -> Elasticsearch:
    auth = None
    if settings.elastic_username and settings.elastic_password:
        auth = (settings.elastic_username, settings.elastic_password)

    return Elasticsearch(
        settings.elastic_host,
        basic_auth=auth,
        verify_certs=settings.elastic_verify_certs,
        request_timeout=30,
    )


es_client = _create_es_client()


def _ensure_index_exists() -> None:
    if not es_client.indices.exists(index=settings.elastic_index):
        es_client.indices.create(index=settings.elastic_index)


@app.get("/")
def root() -> tuple[dict, int]:
    return {
        "service": "flamingo-beavers-backend",
        "status": "ok",
        "index": settings.elastic_index,
    }, 200


@app.get("/health")
def health() -> tuple[dict, int]:
    try:
        elastic_ok = bool(es_client.ping())
        info = es_client.info() if elastic_ok else {}
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


@app.post("/documents")
def create_document() -> tuple[dict, int]:
    payload = request.get_json(silent=True) or {}
    doc_id = payload.get("id")
    content = payload.get("content")

    if not isinstance(content, dict):
        return {
            "error": "Payload must include a JSON object under 'content'."
        }, 400

    try:
        _ensure_index_exists()
        if doc_id:
            result = es_client.index(
                index=settings.elastic_index,
                id=doc_id,
                document=content,
            )
        else:
            result = es_client.index(
                index=settings.elastic_index,
                document=content,
            )
    except Exception as exc:
        return {"error": f"Failed to index document: {exc}"}, 500

    return {
        "result": result.get("result"),
        "id": result.get("_id"),
        "index": result.get("_index"),
    }, 201


@app.get("/documents/<doc_id>")
def get_document(doc_id: str) -> tuple[dict, int]:
    try:
        result = es_client.get(index=settings.elastic_index, id=doc_id)
    except NotFoundError:
        return {"error": "Document not found."}, 404
    except Exception as exc:
        return {"error": f"Failed to fetch document: {exc}"}, 500

    return {
        "id": result.get("_id"),
        "index": result.get("_index"),
        "content": result.get("_source", {}),
    }, 200


if __name__ == "__main__":
    app.run(
        host=settings.flask_host,
        port=settings.flask_port,
        debug=settings.flask_debug,
    )
