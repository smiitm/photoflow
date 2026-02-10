# PhotoFlow
A photo distribution platform powered by vector-based facial indexing and search.

Event organisers upload bulk photos to a project. Attendees visit a shareable guest link, take a selfie (or upload a photo), and instantly see every picture of themselves — with a one-click ZIP download.

---

## Table of Contents

1. [How It Works](#how-it-works)
2. [Architecture Overview](#architecture-overview)
3. [Project Structure](#project-structure)
4. [Database Schema](#database-schema)
5. [API Reference](#api-reference)
6. [Getting Started](#getting-started)
7. [Environment Variables](#environment-variables)
8. [Development Notes](#development-notes)

---

## How It Works

PhotoFlow has two distinct user flows built around a single AI pipeline.

### The Organiser Flow (Ingest → Process → Index)

```
Browser  →  Next.js  →  FastAPI  →  S3 (storage)
                    ↓
                  Redis
                    ↓
               Celery Worker  →  face_recognition  →  PostgreSQL/pgvector
```

1. **Create a Project.** The organiser creates an event project (e.g. "Summer Wedding 2026") via the dashboard. This inserts a row in the `projects` table.

2. **Bulk Upload.** Photos are drag-and-dropped onto the uploader. Each file is POSTed to `POST /projects/{id}/upload`. FastAPI reads the bytes, streams them to a **private AWS S3 bucket** via `boto3`, and immediately inserts a row in the `images` table containing the `s3_key` (the path inside the bucket). The endpoint returns instantly — it does **not** wait for AI processing.

3. **Background Processing.** After saving the S3 key, FastAPI dispatches an async task to **Redis** via **Celery**:
   ```json
   { "task": "worker.process_image", "image_id": "uuid", "s3_key": "project-id/uuid.jpg" }
   ```

4. **AI Extraction.** A Celery worker picks up the task, downloads the image directly from S3 using `boto3.get_object()`, and passes the file to the `face_recognition` library (backed by `dlib`). The library returns:
   - A list of bounding boxes (top, right, bottom, left) for every face found.
   - A **128-dimensional floating-point embedding vector** for each face.

5. **Indexing.** The worker loops through all detected faces and inserts one row per face into the `faces` table, storing the `image_id` foreign key, the `embedding` as a `pgvector` `VECTOR(128)` column, and the `bounding_box` as JSON. **A group photo with 10 people produces 10 rows in `faces`, all pointing to the same `images` row.**

---

### The Attendee Flow (Search → Match → Deliver)

```
Browser (selfie)  →  Next.js  →  FastAPI  →  face_recognition
                                        ↓
                               PostgreSQL (pgvector L2 search)
                                        ↓
                               S3 Presigned URLs  →  Browser
```

1. **Guest Link.** The organiser shares the URL `/guest/{project_id}`. Attendees don't need an account.

2. **Selfie Capture.** The `GuestPortal` component offers two paths:
   - **Live camera** — uses `getUserMedia` to access the webcam, renders a live `<video>` feed with a face-guide overlay, and captures a frame to a `canvas` on button press.
   - **File upload** — a standard file picker for uploading an existing photo from disk.

3. **Server-side Vectorisation.** The selfie is POSTed to `POST /projects/{id}/search`. FastAPI saves it to a temporary file, runs `extract_faces()` synchronously (no Celery — the guest needs an immediate response), extracts the 128-d vector for the **first face found**, then deletes the temp file.

4. **Vector Similarity Search.** FastAPI queries PostgreSQL using `pgvector`'s L2 Euclidean distance operator (`<->`):
   ```sql
   SELECT images.s3_key, faces.embedding <-> '[selfie_vector]' AS distance
   FROM   faces
   JOIN   images ON faces.image_id = images.id
   WHERE  images.project_id = 'project-uuid'
     AND  faces.embedding <-> '[selfie_vector]' < 0.6
   ORDER  BY distance
   LIMIT  20;
   ```
   The threshold `0.6` in L2 space corresponds roughly to "same person" for 128-d dlib embeddings. Duplicate `s3_key` values (same image, multiple matching faces) are deduplicated in Python before returning.

5. **Presigned URL Delivery.** For each matching `s3_key`, FastAPI calls `generate_presigned_url()` to produce a time-limited (1 hour) HTTPS URL that gives the browser temporary read access to the private S3 object. These are returned as JSON.

6. **Gallery + Download.** The `Gallery` component renders matched photos in a responsive masonry grid. The **Download All** button calls `POST /projects/{id}/download-zip` with the list of S3 keys. FastAPI fetches each object directly from S3 using `boto3`, builds a ZIP archive in memory using `zipfile`, and streams it back to the browser via a `StreamingResponse`.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                        CLIENT                           │
│  Next.js 16 + React 19 (TypeScript)                     │
│  Tailwind CSS v4 + shadcn/ui components                 │
│                                                         │
│  /               → Organiser dashboard (project list)   │
│  /project/[id]   → Photo uploader                       │
│  /guest/[id]     → Guest selfie search portal           │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP (fetch)
┌───────────────────────▼─────────────────────────────────┐
│                     BACKEND                             │
│  FastAPI (Python)  –  uvicorn ASGI server               │
│                                                         │
│  POST /projects              → Create project           │
│  GET  /projects              → List projects            │
│  GET  /projects/{id}         → Get project              │
│  PATCH /projects/{id}        → Update project name      │
│  DELETE /projects/{id}       → Delete project + cascade │
│  POST /projects/{id}/upload  → Upload image to S3       │
│  POST /projects/{id}/search  → Selfie face search       │
│  POST /projects/{id}/download-zip → ZIP download        │
└──────┬────────────────────────────────────────┬─────────┘
       │ boto3                                  │ SQLAlchemy
┌──────▼──────┐                        ┌───────▼──────────┐
│   AWS S3    │                        │  PostgreSQL 15   │
│  (private   │                        │  + pgvector ext  │
│   bucket)   │                        │                  │
└─────────────┘                        │  projects        │
                                       │  images          │
       ┌───────────────────────┐       │  faces (VECTOR)  │
       │   Celery Worker       │       └──────────────────┘
       │   (background tasks)  │
       │                       │
       │  process_image task:  │
       │  1. S3 → temp file    │
       │  2. face_recognition  │
       │  3. INSERT faces rows │
       └──────────┬────────────┘
                  │
           ┌──────▼──────┐
           │    Redis     │
           │  (broker +  │
           │   backend)  │
           └─────────────┘
```

**Key design decisions:**

| Decision | Rationale |
|---|---|
| Celery for AI processing | Keeps the upload endpoint instant. Face extraction takes 0.5–5 s per image and must not block the HTTP response. |
| pgvector instead of a dedicated vector DB | Keeps the stack simple — one database for both relational data and similarity search. Works well up to ~1 M faces. |
| Private S3 + presigned URLs | Photos never become publicly guessable URLs. Access is time-limited (1 hour). |
| Direct `get_object()` in Celery worker | Faster than generating a presigned URL and fetching over HTTP; avoids a second round-trip and URL expiry races. |
| Synchronous face extraction on `/search` | Guests need an immediate answer. The selfie is not stored permanently. |
| In-memory ZIP | Avoids temp-file management on the server. Adequate for typical event photo selections (< 200 photos). |

---

## Project Structure

```
photoflow/
├── docker-compose.yml          # PostgreSQL + pgvector, Redis
│
├── backend/
│   ├── main.py                 # FastAPI app, CORS, router registration
│   ├── database.py             # SQLAlchemy engine + session factory
│   ├── models.py               # ORM models: Project, Image, Face
│   ├── schemas.py              # Pydantic v2 request/response schemas
│   ├── deps.py                 # FastAPI dependency providers (get_db)
│   ├── celery_app.py           # Celery instance + Redis configuration
│   ├── worker.py               # Celery task: process_image
│   ├── ai_utils.py             # face_recognition wrapper: extract_faces()
│   ├── s3_utils.py             # boto3 helpers: upload_image(), generate_presigned_url()
│   ├── routers/
│   │   └── projects.py         # All /projects/* endpoints
│   ├── alembic/                # Database migrations
│   ├── requirements.txt
│   └── .env.example            # Template for required secrets
│
└── frontend/
    ├── src/
    │   ├── app/
    │   │   ├── layout.tsx              # Root layout + sticky nav
    │   │   ├── page.tsx                # Organiser dashboard (project list)
    │   │   ├── project/[id]/
    │   │   │   ├── page.tsx            # Project detail page (server component)
    │   │   │   └── uploader.tsx        # Drag-and-drop bulk uploader (client)
    │   │   └── guest/[project_id]/
    │   │       └── page.tsx            # Guest selfie portal (server component)
    │   ├── components/
    │   │   ├── create-project-dialog.tsx  # Dialog for new projects
    │   │   ├── project-card.tsx           # Dashboard project card
    │   │   ├── gallery.tsx               # Masonry photo grid + download
    │   │   └── guest-portal.tsx          # Selfie camera/upload state machine
    │   └── lib/
    │       ├── api.ts                  # fetch wrappers for all API calls
    │       └── utils.ts               # cn() classname utility
    └── package.json
```

---

## Database Schema

### `projects`

| Column | Type | Notes |
|---|---|---|
| `id` | `UUID` PK | Auto-generated |
| `name` | `VARCHAR` | Not null |
| `created_at` | `TIMESTAMPTZ` | Defaults to `now()` |

### `images`

| Column | Type | Notes |
|---|---|---|
| `id` | `UUID` PK | Auto-generated |
| `project_id` | `UUID` FK → projects | Indexed; CASCADE delete |
| `s3_key` | `VARCHAR` | Path in S3, e.g. `{project_id}/{uuid}.jpg` |

### `faces`

| Column | Type | Notes |
|---|---|---|
| `id` | `UUID` PK | Auto-generated |
| `image_id` | `UUID` FK → images | Indexed; CASCADE delete |
| `embedding` | `VECTOR(128)` | 128-d dlib face embedding |
| `bounding_box` | `JSONB` | `{top, right, bottom, left}` pixel coords |

> One image can produce many `faces` rows. Deleting a project cascades through images → faces automatically.

---

## API Reference

| Method | Path | Description |
|---|---|---|
| `POST` | `/projects` | Create a project (`{name}`) |
| `GET` | `/projects` | List all projects with image counts |
| `GET` | `/projects/{id}` | Get a single project |
| `PATCH` | `/projects/{id}` | Update project name |
| `DELETE` | `/projects/{id}` | Delete project (cascades) |
| `POST` | `/projects/{id}/upload` | Upload an image; enqueues AI task |
| `POST` | `/projects/{id}/search` | Submit selfie; returns matching presigned URLs |
| `POST` | `/projects/{id}/download-zip` | Download selected images as ZIP |

Interactive docs available at `http://localhost:8000/docs` when the backend is running.

---

## Getting Started

### Prerequisites

- [Docker Desktop](https://www.docker.com/) (for PostgreSQL + Redis)
- [Python 3.10+](https://www.python.org/)
- [Node.js 18+](https://nodejs.org/)
- An AWS account with an S3 bucket and an IAM user that has `s3:PutObject`, `s3:GetObject`, and `s3:GeneratePresignedUrl` permissions.

---

### 1. Start Infrastructure

```bash
# From the repo root
docker-compose up -d
```

This starts:
- **PostgreSQL 15 + pgvector** on port `5433`
- **Redis** on port `6379`

---

### 2. Configure the Backend

```bash
cd backend
```

**Copy and fill in the environment file:**
```bash
cp .env.example .env
# Edit .env with your AWS credentials and bucket name
```

**Create a virtual environment:**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

**Install dependencies:**
```bash
pip install -r requirements.txt
```

**Run database migrations:**
```bash
alembic upgrade head
```

**Start the API server** (terminal 1):
```bash
uvicorn main:app --reload
```

**Start the Celery worker** (terminal 2, venv activated):
```bash
# Windows (solo pool — multiprocessing not supported on Windows)
celery -A celery_app worker --loglevel=info --pool=solo

# macOS / Linux
celery -A celery_app worker --loglevel=info
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

---

### 3. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:3000`.

---

### 4. Using the App

1. Go to `http://localhost:3000`.
2. Click **Create Project** and give it a name (e.g. "Test Event").
3. On the project page, drag and drop some photos with people in them. Each upload triggers background AI processing.
4. Wait a few seconds for Celery to process the faces (watch the worker terminal).
5. Share the guest link: `http://localhost:3000/guest/{project_id}`.
6. On the guest page, take or upload a selfie. Click **Find My Photos**.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `AWS_ACCESS_KEY_ID` | ✅ | IAM user access key |
| `AWS_SECRET_ACCESS_KEY` | ✅ | IAM user secret |
| `AWS_REGION` | ✅ | S3 bucket region (e.g. `ap-south-1`) |
| `S3_BUCKET_NAME` | ✅ | Name of the private S3 bucket |
| `REDIS_URL` | — | Redis connection string. Defaults to `redis://localhost:6379/0` |
| `DATABASE_URL` | — | PostgreSQL connection string. Defaults to local Docker instance |

---

## Development Notes

### Face Recognition Accuracy

- `face_recognition` uses a 128-dimensional dlib embedding and is very fast on CPU.
- The similarity threshold is currently `0.6` (L2 Euclidean distance). Lower = stricter matching; raise it if you're missing matches, lower it if you're getting false positives.
- For higher accuracy (at the cost of speed), switch to InsightFace's 512-d ArcFace model. The database schema supports this by changing the `VECTOR(128)` column to `VECTOR(512)` in a new migration.
- Photos should be reasonably well-lit and front-facing for best results.

### Scaling Considerations

- **pgvector** performs exact nearest-neighbour search by default. For datasets with > 500k face rows, add an **IVFFlat** or **HNSW** index:
  ```sql
  CREATE INDEX ON faces USING hnsw (embedding vector_l2_ops);
  ```
- The **in-memory ZIP** endpoint (`/download-zip`) loads all requested files into RAM simultaneously. The `MAX_ZIP_KEYS = 200` guard prevents abuse, but consider a streaming approach (writing directly to a temp file and streaming chunks) for very large downloads.
- Add a **pgvector IVFFlat index** after you have enough data — it requires `>= lists * 30` rows to train effectively.

### Adding Authentication

The codebase is pre-wired for auth. Look for the commented `# future auth` markers in `deps.py` and `routers/projects.py`. The pattern is:
1. Add a `get_current_user` dependency in `deps.py`.
2. Inject it into each router endpoint.
3. Add `owner_id` to `Project` and filter/check ownership.
No structural refactor is needed.