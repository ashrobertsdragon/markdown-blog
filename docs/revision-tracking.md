# Revision Tracking API Documentation

## Introduction

The revision tracking API provides endpoints for browsing post commit history, viewing previous
versions, comparing revisions with diffs, and reverting posts to earlier states. All data is backed
by the PostRevision database table and synchronized from the GitHub API.

All endpoints require authentication via a Clerk-issued JWT Bearer token. Only the post author or
an admin can access revision data.

---

## Endpoint: GET /api/posts/{slug}/revisions

### Purpose

List paginated revision history for a post. Returns revisions sorted most-recent-first, each
including commit SHA, author, timestamp, and commit message. Use this endpoint to render a revision
timeline UI or programmatically inspect a post's edit history.

### HTTP Method and URL

```text
GET /api/posts/{slug}/revisions
```

### Authorization

Bearer JWT token required. Only the post's author or an admin may list revisions.

```text
Authorization: Bearer <token>
```

### Request Format

**Path Parameters:**

| Parameter | Type   | Required | Description                   |
| :-------- | :----- | :------- | :---------------------------- |
| `slug`    | string | Yes      | URL slug identifying the post |

**Query Parameters:**

| Parameter | Type    | Required | Default | Constraints | Description                |
| :-------- | :------ | :------- | :------ | :---------- | :------------------------- |
| `skip`    | integer | No       | `0`     | 0 – 10000   | Number of records to skip  |
| `limit`   | integer | No       | `10`    | 1 – 100     | Number of records per page |

```bash
curl -X GET "http://localhost:5000/api/posts/my-post/revisions?skip=0&limit=10" \
  -H "Authorization: Bearer <token>"
```

### Response Format

**JSON Schema (200 OK):**

```json
{
  "type": "object",
  "properties": {
    "revisions": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id":             { "type": "string", "format": "uuid" },
          "commit_sha":     { "type": "string", "description": "Full 40-character commit SHA" },
          "short_sha":      { "type": "string", "description": "First 7 characters of commit SHA" },
          "author_id":      { "type": "string", "format": "uuid" },
          "timestamp":      { "type": "string", "format": "date-time" },
          "relative_time":  { "type": "string", "description": "Human-readable time (e.g. '2 days ago')" },
          "commit_message": { "type": "string" },
          "is_revert":      { "type": "boolean" }
        },
        "required": ["id", "commit_sha", "short_sha", "author_id", "timestamp", "relative_time", "commit_message", "is_revert"]
      }
    },
    "total_count": { "type": "integer" },
    "has_more":    { "type": "boolean" }
  },
  "required": ["revisions", "total_count", "has_more"]
}
```

### Success Response (200 OK)

```json
{
  "revisions": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "commit_sha": "abc123def456abc123def456abc123def456abc1",
      "short_sha": "abc123d",
      "author_id": "f1e2d3c4-b5a6-9870-fedc-ba9876543210",
      "timestamp": "2024-11-10T15:30:00+00:00",
      "relative_time": "2 days ago",
      "commit_message": "Update introduction paragraph",
      "is_revert": false
    }
  ],
  "total_count": 42,
  "has_more": true
}
```

### Error Responses

| Status | Condition                                                | Response Body                                   |
| :----- | :------------------------------------------------------- | :---------------------------------------------- |
| 400    | `skip` outside 0–10000                                   | `{"error": "skip must be between 0 and 10000"}` |
| 400    | `limit` outside 1–100                                    | `{"error": "limit must be between 1 and 100"}`  |
| 401    | Missing or invalid JWT token                             | *(handled by auth middleware)*                  |
| 403    | Authenticated user is not the author and is not an admin | `{"error": "Not authorized to view revisions"}` |
| 404    | No post exists with the given slug                       | `{"error": "Post 'my-post' not found"}`         |
| 500    | Post record exists but has no ID (data integrity issue)  | `{"error": "Post 'my-post' has no ID"}`         |

### Performance Characteristics

- **Target response time:** < 200ms (10 revisions, pagination enabled)
- **Database queries:** Indexed on `(post_id, created_at DESC)`, < 100ms
- **Resource usage:** Single database query; no GitHub API call

---

## Endpoint: GET /api/posts/{slug}/revisions/{sha}

### Purpose

Retrieve a single revision by commit SHA. Returns both the raw markdown content and the sanitized
HTML rendering of the post as it existed at that commit. Includes a flag indicating whether this is
the currently active revision.

### HTTP Method and URL

```text
GET /api/posts/{slug}/revisions/{sha}
```

### Authorization

Bearer JWT token required. Only the post's author or an admin may view individual revisions.

```text
Authorization: Bearer <token>
```

### Request Format

**Path Parameters:**

| Parameter | Type   | Required | Constraints   | Description                    |
| :-------- | :----- | :------- | :------------ | :----------------------------- |
| `slug`    | string | Yes      |               | URL slug identifying the post  |
| `sha`     | string | Yes      | max 100 chars | Full or abbreviated commit SHA |

```bash
curl -X GET "http://localhost:5000/api/posts/my-post/revisions/abc123def456" \
  -H "Authorization: Bearer <token>"
```

### Response Format

**JSON Schema (200 OK):**

```json
{
  "type": "object",
  "properties": {
    "id":               { "type": "string", "format": "uuid" },
    "commit_sha":       { "type": "string", "description": "Full 40-character commit SHA" },
    "short_sha":        { "type": "string", "description": "First 7 characters of commit SHA" },
    "author_id":        { "type": "string", "format": "uuid" },
    "timestamp":        { "type": "string", "format": "date-time" },
    "commit_message":   { "type": "string" },
    "markdown_content": { "type": "string", "description": "Raw markdown content at this revision" },
    "html_content":     { "type": "string", "description": "Sanitized rendered HTML content" },
    "is_current":       { "type": "boolean", "description": "True if this is the most recent revision" },
    "is_revert":        { "type": "boolean" }
  },
  "required": ["id", "commit_sha", "short_sha", "author_id", "timestamp", "commit_message",
               "markdown_content", "html_content", "is_current", "is_revert"]
}
```

### Success Response (200 OK)

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "commit_sha": "abc123def456abc123def456abc123def456abc1",
  "short_sha": "abc123d",
  "author_id": "f1e2d3c4-b5a6-9870-fedc-ba9876543210",
  "timestamp": "2024-11-10T15:30:00+00:00",
  "commit_message": "Update introduction paragraph",
  "markdown_content": "# My Post\n\nUpdated introduction content...",
  "html_content": "<h1>My Post</h1>\n<p>Updated introduction content...</p>",
  "is_current": false,
  "is_revert": false
}
```

### Error Responses

| Status | Condition                                                | Response Body                                      |
| :----- | :------------------------------------------------------- | :------------------------------------------------- |
| 400    | Empty SHA value                                          | `{"error": "SHA cannot be empty"}`                 |
| 400    | SHA exceeds 100 characters                               | `{"error": "SHA length N exceeds maximum of 100"}` |
| 401    | Missing or invalid JWT token                             | *(handled by auth middleware)*                     |
| 403    | Authenticated user is not the author and is not an admin | `{"error": "Not authorized to view revisions"}`    |
| 404    | No post exists with the given slug                       | `{"error": "Post 'my-post' not found"}`            |
| 404    | No revision found for the given SHA                      | `{"error": "Revision not found"}`                  |
| 500    | Post record exists but has no ID (data integrity issue)  | `{"error": "Post 'my-post' has no ID"}`            |

### Performance Characteristics

- **Target response time:** < 200ms (database cache hit)
- **Markdown rendering:** Performed on every request; HTML is not stored in PostRevision
- **Resource usage:** Single database lookup; no GitHub API call when content is cached

---

## Endpoint: GET /api/posts/{slug}/revisions/{sha1}/diff/{sha2}

### Purpose

Generate a line-by-line diff between two revisions identified by their commit SHAs. Returns
structured diff lines annotated with type (`context`, `addition`, or `deletion`). Use this endpoint
to power a diff viewer UI.

### HTTP Method and URL

```text
GET /api/posts/{slug}/revisions/{sha1}/diff/{sha2}
```

### Authorization

Bearer JWT token required. Only the post's author or an admin may compare revisions.

```text
Authorization: Bearer <token>
```

### Request Format

**Path Parameters:**

| Parameter | Type   | Required | Constraints   | Description                               |
| :-------- | :----- | :------- | :------------ | :---------------------------------------- |
| `slug`    | string | Yes      |               | URL slug identifying the post             |
| `sha1`    | string | Yes      | max 100 chars | Commit SHA of the older ("from") revision |
| `sha2`    | string | Yes      | max 100 chars | Commit SHA of the newer ("to") revision   |

```bash
curl -X GET "http://localhost:5000/api/posts/my-post/revisions/abc123/diff/def456" \
  -H "Authorization: Bearer <token>"
```

### Response Format

**JSON Schema (200 OK):**

```json
{
  "type": "object",
  "properties": {
    "from_revision": {
      "type": "object",
      "properties": {
        "sha":       { "type": "string" },
        "short_sha": { "type": "string" },
        "timestamp": { "type": "string", "format": "date-time" },
        "author_id": { "type": "string", "format": "uuid" }
      },
      "required": ["sha", "short_sha", "timestamp", "author_id"]
    },
    "to_revision": {
      "type": "object",
      "properties": {
        "sha":       { "type": "string" },
        "short_sha": { "type": "string" },
        "timestamp": { "type": "string", "format": "date-time" },
        "author_id": { "type": "string", "format": "uuid" }
      },
      "required": ["sha", "short_sha", "timestamp", "author_id"]
    },
    "diff_lines": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type":    { "type": "string", "enum": ["context", "addition", "deletion"] },
          "content": { "type": "string" }
        },
        "required": ["type", "content"]
      }
    }
  },
  "required": ["from_revision", "to_revision", "diff_lines"]
}
```

### Success Response (200 OK)

```json
{
  "from_revision": {
    "sha": "abc123def456abc123def456abc123def456abc1",
    "short_sha": "abc123d",
    "timestamp": "2024-11-09T10:00:00+00:00",
    "author_id": "f1e2d3c4-b5a6-9870-fedc-ba9876543210"
  },
  "to_revision": {
    "sha": "def456abc123def456abc123def456abc123def4",
    "short_sha": "def456a",
    "timestamp": "2024-11-10T15:30:00+00:00",
    "author_id": "f1e2d3c4-b5a6-9870-fedc-ba9876543210"
  },
  "diff_lines": [
    { "type": "context",  "content": "# My Post" },
    { "type": "deletion", "content": "Old introduction paragraph." },
    { "type": "addition", "content": "Updated introduction paragraph." },
    { "type": "context",  "content": "" }
  ]
}
```

### Error Responses

| Status | Condition                                                | Response Body                                                                   |
| :----- | :------------------------------------------------------- | :------------------------------------------------------------------------------ |
| 400    | Empty `sha1` or `sha2`                                   | `{"error": "from_sha cannot be empty"}` / `{"error": "to_sha cannot be empty"}` |
| 400    | SHA exceeds 100 characters                               | `{"error": "from_sha length N exceeds maximum of 100"}`                         |
| 401    | Missing or invalid JWT token                             | *(handled by auth middleware)*                                                  |
| 403    | Authenticated user is not the author and is not an admin | `{"error": "Not authorized to view revisions"}`                                 |
| 404    | No post exists with the given slug                       | `{"error": "Post 'my-post' not found"}`                                         |
| 404    | Either SHA does not match a known revision               | `{"error": "Revision not found"}`                                               |
| 500    | Post record exists but has no ID (data integrity issue)  | `{"error": "Post 'my-post' has no ID"}`                                         |

### Performance Characteristics

- **Target response time:** < 500ms (average post, ~2000 words)
- **Diff algorithm:** Python `difflib` line-based comparison
- **Resource usage:** Two database lookups plus in-memory diff computation

---

## Endpoint: POST /api/posts/{slug}/revert

### Purpose

Revert a post's draft content to a previous revision identified by commit SHA. This creates a new
GitHub commit (message: `"Revert to {short-sha}: {original-message}"`) and a new PostRevision
record. The operation is non-destructive — previous history is preserved. After a successful
revert, the caller is redirected to the post edit page.

### HTTP Method and URL

```text
POST /api/posts/{slug}/revert
```

### Authorization

Bearer JWT token required. Only the post's author or an admin may revert.

```text
Authorization: Bearer <token>
```

### Request Format

**Path Parameters:**

| Parameter | Type   | Required | Description                   |
| :-------- | :----- | :------- | :---------------------------- |
| `slug`    | string | Yes      | URL slug identifying the post |

**Request Body (JSON):**

| Field        | Type   | Required | Constraints   | Description                      |
| :----------- | :----- | :------- | :------------ | :------------------------------- |
| `target_sha` | string | Yes      | max 100 chars | Commit SHA to revert the post to |

```bash
curl -X POST "http://localhost:5000/api/posts/my-post/revert" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"target_sha": "abc123def456"}'
```

### Response Format

**JSON Schema (200 OK):**

```json
{
  "type": "object",
  "properties": {
    "success":        { "type": "boolean", "enum": [true] },
    "message":        { "type": "string", "description": "Confirmation message with short SHA" },
    "new_commit_sha": { "type": "string", "description": "Full SHA of the new revert commit" },
    "redirect_url":   { "type": "string", "description": "Path to the post edit page" }
  },
  "required": ["success", "message", "new_commit_sha", "redirect_url"]
}
```

### Success Response (200 OK)

```json
{
  "success": true,
  "message": "Post reverted to abc123d",
  "new_commit_sha": "xyz789abc123xyz789abc123xyz789abc123xyz7",
  "redirect_url": "/edit/my-post"
}
```

### Error Responses

| Status | Condition                                       | Response Body                                                     |
| :----- | :---------------------------------------------- | :---------------------------------------------------------------- |
| 400    | Request body is missing or not JSON             | `{"error": "Request body must be JSON"}`                          |
| 400    | `target_sha` field is missing                   | `{"error": "Missing required field: target_sha"}`                 |
| 400    | `target_sha` exceeds 100 characters             | `{"error": "target_sha length N exceeds maximum of 100"}`         |
| 401    | Missing or invalid JWT token                    | *(handled by auth middleware)*                                    |
| 403    | User is not the post author and is not an admin | `{"error": "Not authorized: only authors and admins can revert"}` |
| 404    | No post exists with the given slug              | `{"error": "Post 'my-post' not found"}`                           |
| 404    | No revision found for `target_sha`              | `{"error": "Revision not found"}`                                 |
| 500    | GitHub commit or filesystem write failed        | `{"error": "<runtime error message>"}`                            |

### Performance Characteristics

- **Target response time:** < 2 seconds (includes GitHub API commit and database write)
- **Side effects:** Writes draft file to filesystem, creates GitHub commit, creates PostRevision record
- **Failure handling:** If the GitHub commit fails, the filesystem write is rolled back and the
  draft remains unchanged

---

## Testing Examples

### Using curl

#### List Revisions (first page)

```bash
TOKEN="<your_jwt_token>"
curl -X GET "http://localhost:5000/api/posts/my-post/revisions?skip=0&limit=10" \
  -H "Authorization: Bearer $TOKEN"
```

#### Get a Single Revision

```bash
curl -X GET "http://localhost:5000/api/posts/my-post/revisions/abc123def456" \
  -H "Authorization: Bearer $TOKEN"
```

#### Compare Two Revisions

```bash
curl -X GET "http://localhost:5000/api/posts/my-post/revisions/abc123/diff/def456" \
  -H "Authorization: Bearer $TOKEN"
```

#### Revert to a Previous Revision

```bash
curl -X POST "http://localhost:5000/api/posts/my-post/revert" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"target_sha": "abc123def456"}'
```

### Using Python Requests

```python
import requests

BASE_URL = "http://localhost:5000"
TOKEN = "<your_jwt_token>"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
SLUG = "my-post"


def list_revisions(skip: int = 0, limit: int = 10) -> dict:
    response = requests.get(
        f"{BASE_URL}/api/posts/{SLUG}/revisions",
        params={"skip": skip, "limit": limit},
        headers=HEADERS,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def get_revision(sha: str) -> dict:
    response = requests.get(
        f"{BASE_URL}/api/posts/{SLUG}/revisions/{sha}",
        headers=HEADERS,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def compare_revisions(sha1: str, sha2: str) -> dict:
    response = requests.get(
        f"{BASE_URL}/api/posts/{SLUG}/revisions/{sha1}/diff/{sha2}",
        headers=HEADERS,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def revert_to_revision(target_sha: str) -> dict:
    response = requests.post(
        f"{BASE_URL}/api/posts/{SLUG}/revert",
        json={"target_sha": target_sha},
        headers=HEADERS,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()
```

### Using Bash

```bash
#!/bin/bash

BASE_URL="http://localhost:5000"
TOKEN="<your_jwt_token>"
SLUG="my-post"

echo "=== Listing revisions ==="
curl -s -w "\nHTTP %{http_code}\n" \
  -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/posts/$SLUG/revisions?limit=5" | jq .

echo "=== Getting first revision SHA ==="
SHA=$(curl -s \
  -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/posts/$SLUG/revisions?limit=1" \
  | jq -r '.revisions[0].commit_sha')
echo "SHA: $SHA"

echo "=== Viewing that revision ==="
curl -s -w "\nHTTP %{http_code}\n" \
  -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/posts/$SLUG/revisions/$SHA" | jq .
```

---

## Error Codes Reference

| HTTP Status | Meaning               | Typical Cause                                       |
| :---------- | :-------------------- | :-------------------------------------------------- |
| 200         | Success               | Operation completed successfully                    |
| 400         | Bad Request           | Invalid query params, missing/malformed body fields |
| 401         | Unauthorized          | Missing or expired JWT token                        |
| 403         | Forbidden             | Valid token but insufficient permissions            |
| 404         | Not Found             | Post slug or commit SHA does not exist              |
| 500         | Internal Server Error | Data integrity issue or unhandled exception         |
