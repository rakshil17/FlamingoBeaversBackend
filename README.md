# FlamingoBeaversBackend

Flask backend with Elasticsearch for university course management.

## Do We Need One Index?

Yes. For this scope, one index is correct:

- `university-courses`

Use one index while all records are courses with a stable schema. Split into more indices only when you have clearly different entity types, retention rules, or scaling requirements.

## Run

From project root:

```bash
python server/app.py
```

## Environment Variables

Only the essentials are used now:

- `FLASK_DEBUG`
- `FLASK_HOST`
- `FLASK_PORT`
- `ELASTIC_HOST`
- `ELASTIC_API_KEY`
- `ELASTIC_INDEX`

## Startup Behavior

When the app starts, it automatically creates the index (if missing) and upserts one example course (`CS101`).

## Routes

- `GET /` basic status plus startup seed result
- `GET /health` Elasticsearch connectivity status
- `POST /courses` add or update a course (uses `course_code` as doc id)
- `GET /courses/<course_code>` get one course
- `DELETE /courses/<course_code>` delete one course
- `DELETE /courses` clear all course documents in the index

## Terminal Test Commands (Fake Data)

Run these while the app is running.

### 1) Add a new course

```bash
curl -X POST http://localhost:5000/courses \
  -H "Content-Type: application/json" \
  -d '{"course_code":"CS350","title":"Database Systems","description":"Relational modeling, SQL, transactions, and indexing.","department":"Computer Science","instructor":"Dr. Noor Ali","credits":4,"level":"undergraduate","semester":"Spring 2027","tags":["databases","sql"],"prerequisites":["CS240"]}'
```

### 2) Get course info

```bash
curl http://localhost:5000/courses/CS350
```

### 3) Delete one course

```bash
curl -X DELETE http://localhost:5000/courses/CS350
```

### 4) Clear the database (all course docs)

```bash
curl -X DELETE http://localhost:5000/courses
```

### 5) Verify startup-seeded course

```bash
curl http://localhost:5000/courses/CS101
```
