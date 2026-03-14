# FlamingoBeaversBackend

Backend API for Flamingo Beavers, wired to Elasticsearch.

## What This Setup Includes

- Flask API server
- Elasticsearch (single-node, local development)
- Kibana for browsing/search debugging
- Docker Compose for one-command startup
- Local Python run option without Docker for the app

## Project Structure

```
.
|-- .env.example
|-- .gitignore
|-- Dockerfile
|-- docker-compose.yml
|-- requirements.txt
`-- server/
		|-- __init__.py
		|-- app.py
		`-- config.py
```

## Environment Setup

1. `.env` is already included for local development defaults.
2. Update values if needed.

Key values:

- `ELASTIC_HOST` (local default: `http://localhost:9200`)
- `ELASTIC_INDEX` (default: `flamingo-beavers`)
- `FLASK_PORT` (default: `5000`)

## Run With Docker (Recommended)

Start all services:

```bash
docker compose up --build
```

Services:

- Flask API: `http://localhost:5000`
- Elasticsearch: `http://localhost:9200`
- Kibana: `http://localhost:5601`

Stop:

```bash
docker compose down
```

Stop and remove volumes:

```bash
docker compose down -v
```

## Run Flask Locally (Elastic Still via Docker)

1. Start Elasticsearch + Kibana only:

```bash
docker compose up elasticsearch kibana
```

2. Create and activate a virtual environment.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run app:

```bash
flask --app server.app run --host=0.0.0.0 --port=5000
```

## API Endpoints

- `GET /` basic service info
- `GET /health` app + Elasticsearch health
- `POST /documents` index a document
- `GET /documents/<doc_id>` fetch a document by id

### Create Document Example

```bash
curl -X POST http://localhost:5000/documents \
	-H "Content-Type: application/json" \
	-d '{"id":"1","content":{"name":"Flamingo Beavers","type":"demo"}}'
```

### Get Document Example

```bash
curl http://localhost:5000/documents/1
```
