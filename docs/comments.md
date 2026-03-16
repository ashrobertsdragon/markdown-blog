# Comments API Documentation

## Introduction

The comments API provides endpoints for posting, listing, and managing comments on published blog posts.
Comments support flat discussion threads with replies (using @mention convention), rate limiting,
moderation workflows, and real-time updates via Server-Sent Events. All data is persisted to the Comment
database table.

Authentication is optional for reading comments and SSE streams. Authenticated endpoints require a
Clerk-issued JWT Bearer token. Admin endpoints require both authentication and the `admin` role.

---

## Authorization Matrix

| Endpoint                                     | Method | Auth     | Role  | Action                                              |
| :------------------------------------------- | :----- | :------- | :---- | :-------------------------------------------------- |
| `GET /api/posts/{slug}/comments`             | GET    | Optional | Any   | List published comments; admins see pending/deleted |
| `GET /api/posts/{slug}/comments/stream`      | GET    | Optional | Any   | Stream new comments as SSE                          |
| `POST /api/posts/{slug}/comments`            | POST   | Required | Any   | Post top-level comment (rate-limited)               |
| `POST /api/posts/{slug}/comments/{id}/reply` | POST   | Required | Any   | Post reply to comment (rate-limited)                |
| `DELETE /api/posts/{slug}/comments/{id}`     | DELETE | Required | Any   | Delete own comments (hard-delete)                   |
| `PUT /admin/comments/{id}/approve`           | PUT    | Required | admin | Approve pending comment                             |
| `DELETE /admin/comments/{id}`                | DELETE | Required | admin | Soft-delete any comment                             |

---

## Comment Lifecycle

### Creation Flow

1. **User posts comment** via `POST /api/posts/{slug}/comments`
1. **Spam detection** runs automatically; flagged comments enter pending state
1. **Published comments** immediately appear in `/api/posts/{slug}/comments` list
1. **Pending comments** visible only to admins until approved
1. **SSE subscribers** receive real-time notification via stream

### Moderation Flow

Pending comments transition through:

1. **pending** — Flagged by spam detection, awaiting admin review
1. **approved** — Admin calls `PUT /admin/comments/{id}/approve`, becomes published
1. **rejected** — Admin calls `DELETE /admin/comments/{id}`, soft-deleted

Soft-deleted comments remain in the database (preserving reply threads) with `is_deleted=true`.

### Deletion Flow

- **Comment author** hard-deletes own comment: removed from database completely
- **Admins/Post authors** soft-delete any comment: marked deleted, row preserved
- **Hard-deleted comments** break reply chains; use soft-delete to avoid this

---

## Rate Limiting

Rate limits apply to **comment creation only** (`POST` endpoints).

| User Type          | Limit       | Window     |
| :----------------- | :---------- | :--------- |
| Authenticated user | 5 comments  | 60 seconds |
| Admin user         | No limit    | —          |
| Anonymous          | Cannot post | —          |

When rate limit is exceeded, the server responds with **HTTP 429** and includes headers:

```text
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1731684000
Retry-After: 45
```

The response body includes `retry_after` (seconds) and the Unix timestamp of reset time.

---

## Endpoint: GET /api/posts/{slug}/comments

### Purpose

List paginated comments for a post. Authentication is optional. Unauthenticated users see only
published, non-deleted comments. Admins see pending and soft-deleted comments.

### HTTP Method and URL

```text
GET /api/posts/{slug}/comments
```

### Authorization

None required. Optional Bearer JWT token to see admin-only comments.

```text
Authorization: Bearer <token>
```

### Request Format

**Path Parameters:**

| Parameter | Type   | Required | Description                   |
| :-------- | :----- | :------- | :---------------------------- |
| `slug`    | string | Yes      | URL slug identifying the post |

**Query Parameters:**

| Parameter | Type    | Required | Default | Constraints | Description               |
| :-------- | :------ | :------- | :------ | :---------- | :------------------------ |
| `skip`    | integer | No       | `0`     | >= 0        | Number of records to skip |
| `limit`   | integer | No       | `50`    | 1–100       | Records per page          |

```bash
curl -X GET "http://localhost:5000/api/posts/my-post/comments?skip=0&limit=10"
```

### Response Format

**JSON Schema (200 OK):**

```json
{
  "type": "object",
  "properties": {
    "comments": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id":                    { "type": "integer" },
          "post_id":               { "type": "integer" },
          "text":                  { "type": "string" },
          "parent_id":             { "type": "integer", "nullable": true },
          "created_at":            { "type": "string", "format": "date-time" },
          "updated_at":            { "type": "string", "format": "date-time" },
          "is_deleted":            { "type": "boolean" },
          "is_pending_moderation": { "type": "boolean" },
          "is_post_author":        { "type": "boolean" }
        },
        "required": ["id", "post_id", "text", "parent_id", "created_at", "updated_at", "is_deleted", "is_pending_moderation", "is_post_author"]
      }
    },
    "total_count": { "type": "integer" },
    "has_more":    { "type": "boolean" }
  },
  "required": ["comments", "total_count", "has_more"]
}
```

### Success Response (200 OK)

```json
{
  "comments": [
    {
      "id": 1,
      "post_id": 42,
      "text": "Great post!",
      "parent_id": null,
      "created_at": "2024-11-15T10:30:00+00:00",
      "updated_at": "2024-11-15T10:30:00+00:00",
      "is_deleted": false,
      "is_pending_moderation": false,
      "is_post_author": false
    },
    {
      "id": 2,
      "post_id": 42,
      "text": "@user1 Agreed!",
      "parent_id": 1,
      "created_at": "2024-11-15T11:00:00+00:00",
      "updated_at": "2024-11-15T11:00:00+00:00",
      "is_deleted": false,
      "is_pending_moderation": false,
      "is_post_author": false
    }
  ],
  "total_count": 2,
  "has_more": false
}
```

### Error Responses

| Status | Condition                          | Response Body                                  |
| :----- | :--------------------------------- | :--------------------------------------------- |
| 400    | `limit` outside 1–100              | `{"error": "limit must be between 1 and 100"}` |
| 404    | No post exists with the given slug | `{"error": "Post 'my-post' not found"}`        |
| 500    | Unexpected server error            | `{"error": "<error message>"}`                 |

---

## Endpoint: GET /api/posts/{slug}/comments/stream

### Purpose

Opens a persistent Server-Sent Events stream that yields new comments as they are published. Allows
real-time comment feeds on the frontend. Clients may pass `last_comment_id` to resume after a
reconnect and receive only comments posted after that ID.

### HTTP Method and URL

```text
GET /api/posts/{slug}/comments/stream
```

### Authorization

None required. Public endpoint.

### Request Format

**Path Parameters:**

| Parameter | Type   | Required | Description                   |
| :-------- | :----- | :------- | :---------------------------- |
| `slug`    | string | Yes      | URL slug identifying the post |

**Query Parameters:**

| Parameter         | Type    | Required | Description                             |
| :---------------- | :------ | :------- | :-------------------------------------- |
| `last_comment_id` | integer | No       | Comment ID to resume after on reconnect |

```bash
curl -X GET "http://localhost:5000/api/posts/my-post/comments/stream"
```

### Response Format

**SSE Format (200 OK):**

Returns `Content-Type: text/event-stream`. Each new comment is emitted as a `data:` line containing
JSON-serialized comment object.

```text
data: {"id":3,"post_id":42,"text":"Another comment","parent_id":null,"created_at":"2024-11-15T12:00:00+00:00","updated_at":"2024-11-15T12:00:00+00:00","is_deleted":false,"is_pending_moderation":false,"is_post_author":false}
data: {"id":4,"post_id":42,"text":"Reply to #3","parent_id":3,"created_at":"2024-11-15T12:01:00+00:00","updated_at":"2024-11-15T12:01:00+00:00","is_deleted":false,"is_pending_moderation":false,"is_post_author":false}
```

### Reconnection Pattern

1. Client opens SSE connection
1. Client tracks the `id` of the last received comment
1. On disconnect, client reopens connection with `?last_comment_id=<id>`
1. Server streams only comments posted after that ID
1. Client merges with previously buffered comments

```javascript
function connectCommentStream(slug, lastCommentId = null) {
  const url = new URL(`/api/posts/${slug}/comments/stream`, window.location.origin);
  if (lastCommentId) url.searchParams.set('last_comment_id', lastCommentId);

  const eventSource = new EventSource(url);
  eventSource.onmessage = (event) => {
    const comment = JSON.parse(event.data);
    console.log('New comment:', comment);
    lastCommentId = comment.id;
  };
  eventSource.onerror = () => {
    eventSource.close();
    setTimeout(() => connectCommentStream(slug, lastCommentId), 5000);
  };
}
```

### Error Responses

| Status | Condition                                | Response Body                                     |
| :----- | :--------------------------------------- | :------------------------------------------------ |
| 400    | `last_comment_id` is not a valid integer | `{"error": "last_comment_id must be an integer"}` |
| 404    | No post exists with the given slug       | `{"error": "Post 'my-post' not found"}`           |
| 500    | Unexpected server error                  | `{"error": "<error message>"}`                    |

---

## Endpoint: POST /api/posts/{slug}/comments

### Purpose

Post a new top-level comment on a published post. Requires authentication. Subject to rate limiting
(5 per minute per user; bypassed for admins). Spam detection may flag the comment for moderation
without blocking. Published comments immediately appear in list and SSE stream.

### HTTP Method and URL

```text
POST /api/posts/{slug}/comments
```

### Authorization

Bearer JWT token required.

```text
Authorization: Bearer <token>
```

### Request Format

**Path Parameters:**

| Parameter | Type   | Required | Description                   |
| :-------- | :----- | :------- | :---------------------------- |
| `slug`    | string | Yes      | URL slug identifying the post |

**Request Body (JSON):**

| Field  | Type   | Required | Constraints | Description          |
| :----- | :----- | :------- | :---------- | :------------------- |
| `text` | string | Yes      | min 1 char  | Comment text content |

```bash
curl -X POST "http://localhost:5000/api/posts/my-post/comments" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"text": "Great post!"}'
```

### Response Format

**JSON Schema (201 Created):**

```json
{
  "type": "object",
  "properties": {
    "id":                    { "type": "integer" },
    "post_id":               { "type": "integer" },
    "text":                  { "type": "string" },
    "parent_id":             { "type": "integer", "nullable": true },
    "created_at":            { "type": "string", "format": "date-time" },
    "updated_at":            { "type": "string", "format": "date-time" },
    "is_deleted":            { "type": "boolean" },
    "is_pending_moderation": { "type": "boolean" },
    "is_post_author":        { "type": "boolean" }
  },
  "required": ["id", "post_id", "text", "parent_id", "created_at", "updated_at", "is_deleted", "is_pending_moderation", "is_post_author"]
}
```

### Success Response (201 Created)

```json
{
  "id": 5,
  "post_id": 42,
  "text": "Great post!",
  "parent_id": null,
  "created_at": "2024-11-15T13:00:00+00:00",
  "updated_at": "2024-11-15T13:00:00+00:00",
  "is_deleted": false,
  "is_pending_moderation": false,
  "is_post_author": false
}
```

### Response Headers

On success, the response includes rate limit information:

```text
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 3
X-RateLimit-Reset: 1731684060
```

### Error Responses

| Status | Condition                           | Response Body                                                                        |
| :----- | :---------------------------------- | :----------------------------------------------------------------------------------- |
| 400    | Request body is missing or not JSON | `{"error": "Request body must be JSON"}`                                             |
| 400    | `text` field is missing or empty    | `{"error": "Missing required field: text"}`                                          |
| 401    | Missing or invalid JWT token        | *(handled by auth middleware)*                                                       |
| 404    | No post exists with the given slug  | `{"error": "Post not found"}`                                                        |
| 429    | Rate limit exceeded (5 per minute)  | `{"error": "Rate limit exceeded", "code": "rate_limit_exceeded", "retry_after": 45}` |
| 500    | Unexpected server error             | `{"error": "<error message>"}`                                                       |

---

## Endpoint: POST /api/posts/{slug}/comments/{comment_id}/reply

### Purpose

Post a reply to an existing comment. By convention, reply text should be prefixed with `@username`
to mention the parent comment author. Subject to the same rate limiting and spam detection as
top-level comments.

### HTTP Method and URL

```text
POST /api/posts/{slug}/comments/{comment_id}/reply
```

### Authorization

Bearer JWT token required.

```text
Authorization: Bearer <token>
```

### Request Format

**Path Parameters:**

| Parameter    | Type    | Required | Description                   |
| :----------- | :------ | :------- | :---------------------------- |
| `slug`       | string  | Yes      | URL slug identifying the post |
| `comment_id` | integer | Yes      | Parent comment ID             |

**Request Body (JSON):**

| Field  | Type   | Required | Constraints | Description                                           |
| :----- | :----- | :------- | :---------- | :---------------------------------------------------- |
| `text` | string | Yes      | min 1 char  | Reply text content (typically prefixed with @mention) |

```bash
curl -X POST "http://localhost:5000/api/posts/my-post/comments/1/reply" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"text": "@user1 Great point!"}'
```

### Response Format

**JSON Schema (201 Created):**

Same as `POST /api/posts/{slug}/comments` response.

### Success Response (201 Created)

```json
{
  "id": 6,
  "post_id": 42,
  "text": "@user1 Great point!",
  "parent_id": 1,
  "created_at": "2024-11-15T13:30:00+00:00",
  "updated_at": "2024-11-15T13:30:00+00:00",
  "is_deleted": false,
  "is_pending_moderation": false,
  "is_post_author": false
}
```

### Error Responses

| Status | Condition                           | Response Body                                                                        |
| :----- | :---------------------------------- | :----------------------------------------------------------------------------------- |
| 400    | Request body is missing or not JSON | `{"error": "Request body must be JSON"}`                                             |
| 400    | `text` field is missing or empty    | `{"error": "Missing required field: text"}`                                          |
| 401    | Missing or invalid JWT token        | *(handled by auth middleware)*                                                       |
| 404    | Post or parent comment not found    | `{"error": "Comment not found"}`                                                     |
| 429    | Rate limit exceeded (5 per minute)  | `{"error": "Rate limit exceeded", "code": "rate_limit_exceeded", "retry_after": 45}` |
| 500    | Unexpected server error             | `{"error": "<error message>"}`                                                       |

---

## Endpoint: DELETE /api/posts/{slug}/comments/{comment_id}

### Purpose

Delete a comment. Comment authors hard-delete their own comments (removed from database). Admins and
post authors soft-delete any comment (marked deleted, row preserved for thread coherence).

### HTTP Method and URL

```text
DELETE /api/posts/{slug}/comments/{comment_id}
```

### Authorization

Bearer JWT token required.

```text
Authorization: Bearer <token>
```

### Request Format

**Path Parameters:**

| Parameter    | Type    | Required | Description                   |
| :----------- | :------ | :------- | :---------------------------- |
| `slug`       | string  | Yes      | URL slug identifying the post |
| `comment_id` | integer | Yes      | Comment ID to delete          |

```bash
curl -X DELETE "http://localhost:5000/api/posts/my-post/comments/1" \
  -H "Authorization: Bearer <token>"
```

### Response Format

**204 No Content** on success (empty body).

### Error Responses

| Status | Condition                                         | Response Body                                        |
| :----- | :------------------------------------------------ | :--------------------------------------------------- |
| 401    | Missing or invalid JWT token                      | *(handled by auth middleware)*                       |
| 403    | User not comment author and not admin/post author | `{"error": "Not authorized to delete this comment"}` |
| 404    | Post or comment not found                         | `{"error": "Comment not found"}`                     |
| 500    | Unexpected server error                           | `{"error": "<error message>"}`                       |

---

## Endpoint: PUT /admin/comments/{comment_id}/approve

### Purpose

Approve a comment pending moderation. Only accessible to admins. Transitions the comment from
pending to published state.

### HTTP Method and URL

```text
PUT /admin/comments/{comment_id}/approve
```

### Authorization

Bearer JWT token required. User must have `admin` role.

```text
Authorization: Bearer <token>
```

### Request Format

**Path Parameters:**

| Parameter    | Type    | Required | Description           |
| :----------- | :------ | :------- | :-------------------- |
| `comment_id` | integer | Yes      | Comment ID to approve |

```bash
curl -X PUT "http://localhost:5000/api/admin/comments/5/approve" \
  -H "Authorization: Bearer <token>"
```

### Response Format

**JSON Schema (200 OK):**

Returns the updated comment object (same as comment list/create responses).

### Success Response (200 OK)

```json
{
  "id": 5,
  "post_id": 42,
  "text": "Great post!",
  "parent_id": null,
  "created_at": "2024-11-15T13:00:00+00:00",
  "updated_at": "2024-11-15T13:00:00+00:00",
  "is_deleted": false,
  "is_pending_moderation": false,
  "is_post_author": false
}
```

### Error Responses

| Status | Condition                    | Response Body                                      |
| :----- | :--------------------------- | :------------------------------------------------- |
| 401    | Missing or invalid JWT token | *(handled by auth middleware)*                     |
| 403    | User lacks `admin` role      | `{"error": "<message>", "required_role": "admin"}` |
| 404    | Comment not found            | `{"error": "Comment not found"}`                   |
| 500    | Unexpected server error      | `{"error": "<error message>"}`                     |

---

## Endpoint: DELETE /admin/comments/{comment_id}

### Purpose

Soft-delete a comment as admin. Marks the comment as deleted without removing the row, preserving
reply thread coherence.

### HTTP Method and URL

```text
DELETE /admin/comments/{comment_id}
```

### Authorization

Bearer JWT token required. User must have `admin` role.

```text
Authorization: Bearer <token>
```

### Request Format

**Path Parameters:**

| Parameter    | Type    | Required | Description          |
| :----------- | :------ | :------- | :------------------- |
| `comment_id` | integer | Yes      | Comment ID to delete |

```bash
curl -X DELETE "http://localhost:5000/api/admin/comments/5" \
  -H "Authorization: Bearer <token>"
```

### Response Format

**204 No Content** on success (empty body).

### Error Responses

| Status | Condition                    | Response Body                                      |
| :----- | :--------------------------- | :------------------------------------------------- |
| 401    | Missing or invalid JWT token | *(handled by auth middleware)*                     |
| 403    | User lacks `admin` role      | `{"error": "<message>", "required_role": "admin"}` |
| 404    | Comment not found            | `{"error": "Comment not found"}`                   |
| 500    | Unexpected server error      | `{"error": "<error message>"}`                     |

---

## Testing Examples

### Using curl

#### List Comments

```bash
TOKEN="<your_jwt_token>"
curl -X GET "http://localhost:5000/api/posts/my-post/comments?skip=0&limit=10"
```

#### Post a Comment

```bash
curl -X POST "http://localhost:5000/api/posts/my-post/comments" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "Great post!"}'
```

#### Reply to a Comment

```bash
curl -X POST "http://localhost:5000/api/posts/my-post/comments/1/reply" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "@user1 Agreed!"}'
```

#### Delete a Comment

```bash
curl -X DELETE "http://localhost:5000/api/posts/my-post/comments/5" \
  -H "Authorization: Bearer $TOKEN"
```

#### Approve a Pending Comment (admin only)

```bash
curl -X PUT "http://localhost:5000/api/admin/comments/5/approve" \
  -H "Authorization: Bearer $TOKEN"
```

### Using Python Requests

```python
import requests

BASE_URL = "http://localhost:5000"
TOKEN = "<your_jwt_token>"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
SLUG = "my-post"


def list_comments(skip: int = 0, limit: int = 50) -> dict:
    response = requests.get(
        f"{BASE_URL}/api/posts/{SLUG}/comments",
        params={"skip": skip, "limit": limit},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def post_comment(text: str) -> dict:
    response = requests.post(
        f"{BASE_URL}/api/posts/{SLUG}/comments",
        json={"text": text},
        headers=HEADERS,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def reply_to_comment(comment_id: int, text: str) -> dict:
    response = requests.post(
        f"{BASE_URL}/api/posts/{SLUG}/comments/{comment_id}/reply",
        json={"text": text},
        headers=HEADERS,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def delete_comment(comment_id: int) -> None:
    response = requests.delete(
        f"{BASE_URL}/api/posts/{SLUG}/comments/{comment_id}",
        headers=HEADERS,
        timeout=10,
    )
    response.raise_for_status()


def approve_comment(comment_id: int) -> dict:
    response = requests.put(
        f"{BASE_URL}/api/admin/comments/{comment_id}/approve",
        headers=HEADERS,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()
```

### Stream Comments with JavaScript EventSource

```javascript
function connectCommentStream(slug) {
  const eventSource = new EventSource(`/api/posts/${slug}/comments/stream`);

  eventSource.onmessage = (event) => {
    const comment = JSON.parse(event.data);
    console.log('New comment:', comment);
    displayComment(comment);
  };

  eventSource.onerror = () => {
    console.error('Stream error, reconnecting...');
    eventSource.close();
    setTimeout(() => connectCommentStream(slug), 5000);
  };

  return eventSource;
}

function displayComment(comment) {
  const container = document.getElementById('comments');
  const el = document.createElement('div');
  el.className = comment.is_post_author ? 'comment author-badge' : 'comment';
  el.innerHTML = `
    <p><strong>${comment.is_post_author ? 'Author' : 'Commenter'}</strong></p>
    <p>${escapeHtml(comment.text)}</p>
    <small>${new Date(comment.created_at).toLocaleString()}</small>
  `;
  container.appendChild(el);
}
```

---

## Error Codes Reference

| HTTP Status | Meaning               | Typical Cause                                |
| :---------- | :-------------------- | :------------------------------------------- |
| 200         | Success               | Operation completed successfully             |
| 201         | Created               | Comment posted successfully                  |
| 204         | No Content            | Comment deleted successfully                 |
| 400         | Bad Request           | Invalid query params, missing/malformed body |
| 401         | Unauthorized          | Missing or expired JWT token                 |
| 403         | Forbidden             | Valid token but insufficient permissions     |
| 404         | Not Found             | Post or comment does not exist               |
| 429         | Rate Limited          | Comment creation rate limit exceeded         |
| 500         | Internal Server Error | Unexpected server error                      |
