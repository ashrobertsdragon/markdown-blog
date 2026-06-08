# Blog Platform — Flask Backend

A Flask application providing the REST API for the blog platform. The backend is structured around Domain-Driven Design (DDD) principles using Hexagonal Architecture, separating business logic from infrastructure concerns. It is deployed via Phusion Passenger on cPanel and uses [uv](https://docs.astral.sh/uv/) for Python package management.

---

## Running Locally

This project uses `uv` exclusively. Do not use `pip`, `pip install`, or activate virtual environments manually — `uv run` handles all of that automatically.

```bash
# Install or sync dependencies
cd monorepo/backend
uv sync

# Start the development server
uv run flask --app src/backend/main.py run --debug

# Run the full test suite
uv run pytest

# Run linting and formatting
uv run ruff check --fix .
uv run ruff format .

# Run type checking
uv run mypy .
```

Background job scripts (intended for cron):

```bash
uv run src/scripts/process_notifications.py
uv run src/scripts/sync_repo_changes.py
uv run src/scripts/cleanup_revisions.py
```

---

## Architecture

The backend is organized into five layers, each with a distinct responsibility boundary.

### Domain (`src/backend/domain/`)

The innermost layer. Contains all business rules with no outward dependencies. Structured around:

- **Aggregates** — consistency boundaries: `Post`, `User`, `Comment`, `Notification`, `PostRevision`
- **Value Objects** — immutable, self-validating types: `Slug`, `MarkdownContent`, `HtmlContent`, `CommitSHA`, `EmailAddress`, `Role`
- **Domain Events** — signals emitted when state changes: `DraftCreated`, `PostPublished`, `CommentPosted`, `ReplyReceived`

### Application (`src/backend/application/`)

Orchestrates use cases by coordinating domain objects and infrastructure ports. Split into:

- **Commands** — write operations that mutate state (e.g., create draft, publish post, delete comment)
- **Queries** — read operations that return projections without mutating state
- **Handlers** — one handler per command or query; thin coordinators, no business logic

### Infrastructure (`src/backend/infrastructure/`)

Adapters connecting the application to external systems:

- **Persistence** — SQLModel models, database session management
- **Filesystem** — `FileSystemDraftRepository` handles all draft markdown I/O
- **GitHub** — sync service and revision service wrapping the GitHub REST API
- **Email** — Resend integration for outbound notifications
- **Auth** — Clerk JWT verification adapter
- **Monitoring** — in-memory error logger (see [Error Logging](#error-logging))

### API (`src/backend/api/`)

Flask HTTP layer. Each concern is a Blueprint:

| Blueprint           | Prefix          | Responsibility                    |
| ------------------- | --------------- | --------------------------------- |
| `posts_bp`          | `/api/posts`    | Post CRUD, draft lifecycle        |
| `comments_bp`       | `/api/comments` | Public comment operations         |
| `auth_bp`           | `/api/auth`     | Authentication endpoints          |
| `admin_bp`          | `/api/admin`    | Admin post/user/system operations |
| `admin_comments_bp` | `/api/admin`    | Admin comment moderation          |
| `health_bp`         | `/api`          | Health check                      |

Middleware:

- `auth_middleware` — validates Clerk JWTs and attaches the decoded user to `g`
- `rate_limiter` — per-user and per-IP rate limiting for comment endpoints
- `error_handler` — normalizes exceptions to JSON responses and feeds the error logger

### Scripts (`src/scripts/`)

Standalone Python scripts designed to be invoked by cron. They import application layer handlers directly and have no Flask context dependency.

---

## Admin API

All admin endpoints require the request to carry a valid JWT in the `Authorization` header with the `admin` role. Requests that omit the header or carry a non-admin token receive `403 Forbidden`.

```http
Authorization: Bearer $ADMIN_TOKEN
```

### Post Operations

#### Unpublish a Post

Reverts a published post back to draft status. The post record remains in the database; its state transitions from `published` to `draft`.

```http
POST /api/admin/posts/<post_id>/unpublish
```

```bash
curl -X POST https://example.com/api/admin/posts/42/unpublish \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Success** `200 OK`:

```json
{ "message": "Post unpublished" }
```

**Errors**:

| Status            | Condition                          |
| ----------------- | ---------------------------------- |
| `400 Bad Request` | Post is already in draft state     |
| `403 Forbidden`   | JWT missing or role is not `admin` |
| `404 Not Found`   | No post with the given ID          |

---

### User Operations

#### Get User Activity

Returns a summary of a user's recent platform activity.

```http
GET /api/admin/users/<user_id>/activity
```

```bash
curl https://example.com/api/admin/users/7/activity \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Success** `200 OK`:

```json
{
  "user_id": 7,
  "last_login": "2026-06-01T14:32:00Z",
  "posts_count": 12,
  "comments_count": 34,
  "recent_posts": [
    { "id": 1, "slug": "my-first-post", "title": "My First Post", "published": true, "created_at": "2026-01-15T10:00:00Z" }
  ],
  "recent_comments": [
    { "id": 42, "post_slug": "my-first-post", "text": "Great article!", "created_at": "2026-06-01T09:00:00Z" }
  ]
}
```

`last_login` is `null` if the user has never logged in. `recent_posts` contains up to 5 post objects; `recent_comments` contains up to 10 comment objects. Each object shape is determined by the aggregate's `to_dict()` method.

**Errors**:

| Status          | Condition                          |
| --------------- | ---------------------------------- |
| `403 Forbidden` | JWT missing or role is not `admin` |
| `404 Not Found` | No user with the given ID          |

---

### System Operations

#### System Health Snapshot

Returns the current health of the API and database, plus total uptime in seconds.

```http
GET /api/admin/system/health
```

```bash
curl https://example.com/api/admin/system/health \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Success** `200 OK`:

```json
{
  "api_status": "healthy",
  "database_status": "healthy",
  "uptime": 86400
}
```

Each status field is one of `healthy`, `degraded`, or `unhealthy`.

**Errors**:

| Status          | Condition                          |
| --------------- | ---------------------------------- |
| `403 Forbidden` | JWT missing or role is not `admin` |

---

#### Recent Error Logs

Returns recent application errors captured by the in-memory error logger, newest first.

```http
GET /api/admin/system/errors?limit=<N>
```

`limit` is optional, must be between 1 and 100, defaults to 50.

```bash
curl "https://example.com/api/admin/system/errors?limit=20" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Success** `200 OK`:

```json
{
  "errors": [
    {
      "timestamp": "2026-06-07T09:15:00Z",
      "message": "Database connection timeout",
      "stack_trace": "...",
      "endpoint": "/api/posts"
    }
  ]
}
```

`endpoint` is `null` if the error occurred outside a request context.

**Errors**:

| Status          | Condition                          |
| --------------- | ---------------------------------- |
| `403 Forbidden` | JWT missing or role is not `admin` |

---

### Comment Moderation

#### Delete a Comment (Admin)

Soft-deletes a comment, preserving the database row so reply threads remain coherent. The comment body is cleared and the row is marked as deleted.

```http
DELETE /api/admin/comments/<comment_id>
```

```bash
curl -X DELETE https://example.com/api/admin/comments/99 \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Success** `204 No Content`

**Errors**:

| Status          | Condition                          |
| --------------- | ---------------------------------- |
| `403 Forbidden` | JWT missing or role is not `admin` |
| `404 Not Found` | No comment with the given ID       |

---

#### Approve a Comment

Approves a comment that is pending moderation, making it publicly visible.

```http
PUT /api/admin/comments/<comment_id>/approve
```

```bash
curl -X PUT https://example.com/api/admin/comments/99/approve \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Success** `200 OK`

**Errors**:

| Status          | Condition                          |
| --------------- | ---------------------------------- |
| `403 Forbidden` | JWT missing or role is not `admin` |
| `404 Not Found` | No comment with the given ID       |

---

## Command and Query Handlers

The application layer exposes typed command and query objects. Handlers receive these objects, coordinate domain and infrastructure, and return results. They contain no HTTP-specific logic.

### Commands

**`UnpublishPostCommand`** (`src/backend/application/commands/`)

Fields: `post_id: int`, `author_id: int`, `user_role: str`

Loads the `Post` aggregate, verifies the caller has the `admin` role, transitions the post state from `published` to `draft`, and persists the change. Raises `PermissionError` if `user_role` is not `admin`, and `ValueError` if the post is already in draft state.

---

**`DeleteCommentCommand`** (`src/backend/application/commands/`)

Fields: `comment_id: int`, `author_id: int`, `user_role: str`

Behavior varies by caller identity:

- **Admin** (`user_role == "admin"`) — soft-deletes the comment, preserving the row
- **Owner** (`author_id` matches the comment's author) — hard-deletes the comment row

Raises `PermissionError` if the caller is neither admin nor the comment's author.

---

### Queries

**`GetUserActivityQuery`** (`src/backend/application/queries/`)

Fields: `user_id: int`

Returns a `UserActivity` projection containing: `last_login` (datetime or None), `posts_count` (int), `comments_count` (int), `recent_posts` (up to 5 most recent), `recent_comments` (up to 10 most recent). Raises `LookupError` if no user exists with `user_id`.

---

**`GetSystemHealthQuery`** (`src/backend/application/queries/`)

Takes no fields. Returns a `SystemHealth` projection containing: `api_status` (str), `database_status` (str), `uptime` (int, seconds since process start). Database status is determined by issuing a lightweight probe query; a failure downgrades the status without raising an exception.

---

## Error Logging

**`ErrorLogger`** lives in `src/backend/infrastructure/monitoring/`. It is an in-memory ring buffer capped at 50 entries and is thread-safe.

### Interface

| Method                                      | Description                                                                                       |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| `log_error(message, stack_trace, endpoint)` | Appends an entry. `endpoint` may be `None`. When the buffer is full, the oldest entry is evicted. |
| `get_recent_errors(limit)`                  | Returns up to `limit` entries, newest first.                                                      |
| `clear()`                                   | Empties the buffer. Intended for use in tests.                                                    |

### Flask Integration

The `error_handler` middleware registers a Flask `@app.errorhandler` that catches all unhandled exceptions. For each exception it:

1. Formats a stack trace via the standard `traceback` module
1. Calls `ErrorLogger.log_error` with the formatted trace and the current `request.path` (or `None` outside a request context)
1. Returns a normalized JSON error response to the client

Because the buffer is in-memory, entries do not survive a process restart. For persistent error tracking, tail `logs/stderr.log` or integrate an external sink.

---

## Testing

Run the full suite from the `backend` directory:

```bash
cd monorepo/backend
uv run pytest
```

Run a specific subset:

```bash
uv run pytest tests/unit          # Domain and value object tests
uv run pytest tests/integration   # Repository and API endpoint tests
uv run pytest tests/e2e           # Full workflow tests
```

Generate a coverage report:

```bash
uv run pytest --cov=src/backend --cov-report=html
```

### Coverage Targets

| Layer          | Target |
| -------------- | ------ |
| Domain         | 90%+   |
| Application    | 85%+   |
| Infrastructure | 70%+   |
| API            | 80%+   |

CI enforces these thresholds on every push to `main`.

---

## Troubleshooting

### 403 Forbidden on Admin Endpoints

The JWT is either missing, expired, or the decoded `role` claim is not `admin`. Verify the token is being sent in the `Authorization: Bearer <token>` header and that it was issued with the admin role by Clerk.

### 404 Not Found

The resource ID in the URL does not correspond to any record in the database. Confirm the correct ID is being used and that the record has not been deleted.

### Database Connection Errors

The cPanel server firewall blocks external access to PostgreSQL on port 5432. The application must connect via `DB_HOST=localhost` (Unix socket or loopback). Check that `DB_HOST` in the environment is set to `localhost`, not a remote hostname.

### Passenger Not Picking Up Changes

After deploying new code, Passenger must be signalled to restart:

```bash
# Replace <cpanel-username> with your cPanel account name
touch ~/<cpanel-username>/tmp/restart.txt
```

Passenger detects this file modification and gracefully reloads the application on the next request.

### Inspecting Recent Errors

Two methods are available:

1. **Via the API** (requires admin JWT):

   ```bash
   curl "https://example.com/api/admin/system/errors?limit=50" \
     -H "Authorization: Bearer $ADMIN_TOKEN"
   ```

1. **Via the log file** on the server (survives restarts, unlike the in-memory buffer):

   ```bash
   tail -f logs/stderr.log
   ```

The in-memory buffer holds at most 50 entries and is cleared on process restart. `logs/stderr.log` is the authoritative source for historical errors.
