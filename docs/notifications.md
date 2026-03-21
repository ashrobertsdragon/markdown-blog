# Notifications API Documentation

## Introduction

The notifications API provides endpoints for managing email notifications on published blog posts.
Users control their notification preferences (comment replies, mentions, new posts), admins monitor
delivery status and retry queues, and email unsubscribe links use cryptographically signed tokens.
All notification data flows through a Resend email service with automatic retry logic and background
cron job processing.

Authentication is required for user preference endpoints and admin monitoring. The unsubscribe endpoint
is unauthenticated but secured by HMAC token verification. All authenticated endpoints require a
Clerk-issued JWT Bearer token.

---

## Authorization Matrix

| Endpoint                                 | Method | Auth     | Role  | Action                                       |
| :--------------------------------------- | :----- | :------- | :---- | :------------------------------------------- |
| `GET /api/user/notification-preferences` | GET    | Required | Any   | Retrieve notification preferences            |
| `PUT /api/user/notification-preferences` | PUT    | Required | Any   | Update notification preferences (partial)    |
| `GET /api/admin/notifications`           | GET    | Required | admin | List all notifications for monitoring        |
| `GET /api/unsubscribe`                   | GET    | None     | N/A   | Unsubscribe via HMAC token (public endpoint) |

---

## Notification Lifecycle

### Event Flow

1. **User action triggers event**: Comment posted, reply received, or mention detected
1. **Notification created**: Domain event generates new Notification record with `status=pending`
1. **Background job processes queue**: Cron job (runs every minute) picks up pending notifications
1. **Delivery via Resend**: Notification service sends email using Resend API
1. **Status updated**: On success, `status=sent` and `sent_at` recorded; on failure, `attempt_count` incremented
1. **Retry logic applied**: Failed notifications retry with exponential backoff (1m, 5m, 15m)
1. **Permanent failure after 3 attempts**: After max retries, `status=failed_permanently`
1. **User unsubscribe**: User clicks unsubscribe link in email, disables all notification preferences

### Preference System

User preferences control which event types trigger notifications:

- `notify_on_comment_replies`: Email when someone replies to user's comment
- `notify_on_mentions`: Email when mentioned (@username) in a comment
- `notify_on_new_posts`: Email when new blog posts are published

Default: All preferences enabled on first access.

### Admin Monitoring

The admin notification list shows:

- All notifications regardless of delivery status (pending, sent, failed, failed_permanently)
- Attempt count and timestamps for debugging retry loops
- Has_delivery_error flag for identifying problem notifications
- PII-safe: Error message details not exposed in API response

---

## Endpoint: GET /api/user/notification-preferences

### Purpose

Retrieve the authenticated user's notification preferences. Auto-creates default preferences
(all enabled) on first access.

### HTTP Method and URL

```text
GET /api/user/notification-preferences
```

### Authorization

Bearer JWT token required.

```text
Authorization: Bearer <token>
```

### Request Format

No request body required.

```bash
curl -X GET "http://localhost:5000/api/user/notification-preferences" \
  -H "Authorization: Bearer <token>"
```

### Response Format

**JSON Schema (200 OK):**

```json
{
  "type": "object",
  "properties": {
    "preferences": {
      "type": "object",
      "properties": {
        "user_id": { "type": "integer" },
        "notify_on_comment_replies": { "type": "boolean" },
        "notify_on_mentions": { "type": "boolean" },
        "notify_on_new_posts": { "type": "boolean" }
      },
      "required": ["user_id", "notify_on_comment_replies", "notify_on_mentions", "notify_on_new_posts"]
    }
  },
  "required": ["preferences"]
}
```

### Success Response (200 OK)

```json
{
  "preferences": {
    "user_id": 42,
    "notify_on_comment_replies": true,
    "notify_on_mentions": true,
    "notify_on_new_posts": true
  }
}
```

### Error Responses

| Status | Condition                    | Response Body                  |
| :----- | :--------------------------- | :----------------------------- |
| 401    | Missing or invalid JWT token | *(handled by auth middleware)* |
| 500    | Unexpected server error      | `{"error": "<error message>"}` |

---

## Endpoint: PUT /api/user/notification-preferences

### Purpose

Update notification preferences for the authenticated user. Accepts partial updates — only provided
fields are modified.

### HTTP Method and URL

```text
PUT /api/user/notification-preferences
```

### Authorization

Bearer JWT token required.

```text
Authorization: Bearer <token>
```

### Request Format

**Request Body (JSON):**

At least one field is required. All fields are optional booleans.

| Field                       | Type    | Required | Description                             |
| :-------------------------- | :------ | :------- | :-------------------------------------- |
| `notify_on_comment_replies` | boolean | No       | Whether to send emails for reply events |
| `notify_on_mentions`        | boolean | No       | Whether to send emails for mentions     |
| `notify_on_new_posts`       | boolean | No       | Whether to send emails for new posts    |

```bash
curl -X PUT "http://localhost:5000/api/user/notification-preferences" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"notify_on_mentions": false}'
```

### Response Format

**JSON Schema (200 OK):**

Same as GET endpoint.

### Success Response (200 OK)

```json
{
  "preferences": {
    "user_id": 42,
    "notify_on_comment_replies": true,
    "notify_on_mentions": false,
    "notify_on_new_posts": true
  }
}
```

### Error Responses

| Status | Condition                           | Response Body                                               |
| :----- | :---------------------------------- | :---------------------------------------------------------- |
| 400    | No body or empty body provided      | `{"error": "At least one preference field is required"}`    |
| 400    | Unknown preference field in request | `{"error": "Unknown preference field: notify_on_invalid"}`  |
| 400    | Field value is not a boolean        | `{"error": "Field 'notify_on_mentions' must be a boolean"}` |
| 401    | Missing or invalid JWT token        | *(handled by auth middleware)*                              |
| 500    | Unexpected server error             | `{"error": "<error message>"}`                              |

---

## Endpoint: GET /api/admin/notifications

### Purpose

List all notifications in the system for admin monitoring and debugging. Returns paginated results
sorted newest-first. Only accessible to admins. Includes delivery status, attempt counts, and
timestamps for analyzing retry behavior.

### HTTP Method and URL

```text
GET /api/admin/notifications
```

### Authorization

Bearer JWT token required. User must have `admin` role.

```text
Authorization: Bearer <token>
```

### Request Format

**Query Parameters:**

| Parameter | Type    | Required | Default | Constraints | Description               |
| :-------- | :------ | :------- | :------ | :---------- | :------------------------ |
| `skip`    | integer | No       | `0`     | >= 0        | Number of records to skip |
| `limit`   | integer | No       | `50`    | 1–200       | Records per page          |

```bash
curl -X GET "http://localhost:5000/api/admin/notifications?skip=0&limit=50" \
  -H "Authorization: Bearer <token>"
```

### Response Format

**JSON Schema (200 OK):**

```json
{
  "type": "object",
  "properties": {
    "notifications": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": { "type": "integer" },
          "recipient_id": { "type": "integer" },
          "sender_id": { "type": "integer", "nullable": true },
          "event_type": { "type": "string", "enum": ["comment_posted", "reply_received", "mention"] },
          "post_id": { "type": "integer", "nullable": true },
          "comment_id": { "type": "integer", "nullable": true },
          "status": { "type": "string", "enum": ["pending", "sent", "failed", "failed_permanently"] },
          "attempt_count": { "type": "integer" },
          "created_at": { "type": "string", "format": "date-time" },
          "sent_at": { "type": "string", "format": "date-time", "nullable": true },
          "has_delivery_error": { "type": "boolean" }
        }
      }
    },
    "skip": { "type": "integer" },
    "limit": { "type": "integer" },
    "total": { "type": "integer" }
  },
  "required": ["notifications", "skip", "limit", "total"]
}
```

### Success Response (200 OK)

```json
{
  "notifications": [
    {
      "id": 1,
      "recipient_id": 42,
      "sender_id": 1,
      "event_type": "comment_posted",
      "post_id": 10,
      "comment_id": 5,
      "status": "sent",
      "attempt_count": 1,
      "created_at": "2024-11-15T10:30:00+00:00",
      "sent_at": "2024-11-15T10:31:00+00:00",
      "has_delivery_error": false
    },
    {
      "id": 2,
      "recipient_id": 42,
      "sender_id": null,
      "event_type": "mention",
      "post_id": 11,
      "comment_id": 8,
      "status": "failed",
      "attempt_count": 2,
      "created_at": "2024-11-15T11:00:00+00:00",
      "sent_at": null,
      "has_delivery_error": true
    }
  ],
  "skip": 0,
  "limit": 50,
  "total": 42
}
```

### Error Responses

| Status | Condition                    | Response Body                                      |
| :----- | :--------------------------- | :------------------------------------------------- |
| 400    | `skip` is negative           | `{"error": "skip must be non-negative"}`           |
| 400    | `limit` outside 1–200        | `{"error": "limit must be between 1 and 200"}`     |
| 401    | Missing or invalid JWT token | *(handled by auth middleware)*                     |
| 403    | User lacks `admin` role      | `{"error": "<message>", "required_role": "admin"}` |
| 500    | Unexpected server error      | `{"error": "<error message>"}`                     |

---

## Endpoint: GET /api/unsubscribe

### Purpose

Unsubscribe a user from all notifications via a secure HMAC token. This endpoint is **unauthenticated**.
The token replaces authentication by proving the caller possesses the shared secret (UNSUBSCRIBE_SECRET).
Typically accessed via email unsubscribe link generated by the notification service.

### HTTP Method and URL

```text
GET /api/unsubscribe
```

### Authorization

None. Public endpoint secured by HMAC token.

```text
(no Authorization header required)
```

### Request Format

**Query Parameters:**

| Parameter | Type    | Required | Constraints       | Description                         |
| :-------- | :------ | :------- | :---------------- | :---------------------------------- |
| `user_id` | integer | Yes      | >= 1              | User ID to unsubscribe              |
| `token`   | string  | Yes      | 64 hex characters | HMAC-SHA256 digest for verification |

```bash
# Token generated by: hmac_sha256(user_id, UNSUBSCRIBE_SECRET).hexdigest()
curl -X GET "http://localhost:5000/api/unsubscribe?user_id=42&token=a1b2c3d4e5f6..." \
  -H "Content-Type: application/json"
```

### Response Format

**JSON Schema (200 OK):**

```json
{
  "type": "object",
  "properties": {
    "message": { "type": "string" },
    "user_id": { "type": "integer" }
  },
  "required": ["message", "user_id"]
}
```

### Success Response (200 OK)

```json
{
  "message": "Successfully unsubscribed from all notifications",
  "user_id": 42
}
```

### Error Responses

| Status | Condition                                               | Response Body                                       |
| :----- | :------------------------------------------------------ | :-------------------------------------------------- |
| 400    | `user_id` query parameter is missing                    | `{"error": "Missing required parameter: user_id"}`  |
| 400    | `token` query parameter is missing or empty             | `{"error": "Missing required parameter: token"}`    |
| 400    | Token does not match the HMAC digest (invalid/tampered) | `{"error": "Invalid or expired unsubscribe token"}` |
| 400    | User with the given `user_id` does not exist            | `{"error": "Invalid unsubscribe request"}`          |
| 500    | Unexpected server error                                 | `{"error": "<error message>"}`                      |

---

## Setup and Configuration

### Environment Variables

Two environment variables are required for notification functionality:

#### RESEND_API_KEY

The API key for the Resend email service. Used to send outbound email notifications.

```bash
export RESEND_API_KEY="re_xxxxxxxxxxxxx"
```

- Obtain from: <https://resend.com> (create account and API keys section)
- Used by: Email service layer to authenticate with Resend API
- Required for: Production email delivery
- Never commit: Store in environment variables or secrets management only

#### UNSUBSCRIBE_SECRET

A cryptographic secret used to generate and verify HMAC tokens in unsubscribe links.
Tokens are generated as: `hmac_sha256(user_id, UNSUBSCRIBE_SECRET).hexdigest()`

```bash
export UNSUBSCRIBE_SECRET="your_secret_key_here_min_32_chars"
```

- Generate: Use a secure random string (minimum 32 characters recommended)
- Used by: Notification service to sign unsubscribe URLs, `GET /unsubscribe` to verify tokens
- Never commit: Store in environment variables or secrets management only
- Rotate carefully: Changing this value invalidates all existing unsubscribe links

### Email Template Setup

Notifications are sent using Resend templates. Set up email templates in your Resend account with
the following event types:

- **comment_posted**: New comment on user's post
- **reply_received**: Reply to user's comment
- **mention**: User mentioned (@username) in a comment
- **new_post**: New blog post published

Each template should include:

- Event details (post slug, comment text, author name)
- Unsubscribe link: `{DOMAIN}/api/unsubscribe?user_id={user_id}&token={token}`
- Preference link: `{DOMAIN}/settings/notifications`

---

## Retry Logic

Notification delivery failures trigger automatic retry with exponential backoff.

### Retry Schedule

| Attempt | Delay After Failure | Cumulative Time |
| :------ | :------------------ | :-------------- |
| 1       | —                   | —               |
| 2       | 1 minute            | 1 minute        |
| 3       | 5 minutes           | 6 minutes       |
| 4       | 15 minutes          | 21 minutes      |
| Failed  | No retry            | Permanent fail  |

### Failure Causes

Retryable failures (transient):

- Network timeout or temporary Resend service unavailability
- Rate limit responses from Resend API

Non-retryable failures (permanent):

- Invalid email address format
- Recipient address blacklisted or bouncing
- Invalid Resend API credentials (RESEND_API_KEY)

### Background Job Processing

A cron job runs every minute to process the notification queue:

```bash
# Run via cron scheduler: * * * * *
uv run scripts/process_notifications.py
```

The job:

1. Queries all `pending` notifications
1. Batches them by event type for efficiency
1. Sends via Resend email service
1. Updates status and timestamps
1. Increments `attempt_count` on failure
1. Sets `status=failed_permanently` after max retries

### Monitoring Retry Behavior

Use the admin notifications endpoint to monitor stuck notifications:

```bash
curl -X GET "http://localhost:5000/api/admin/notifications?limit=10" \
  -H "Authorization: Bearer <token>" \
  | jq '.notifications[] | select(.status == "failed" or .status == "pending")'
```

Look for:

- Notifications with `attempt_count >= 3` in `failed` state (should transition to `failed_permanently`)
- Very old `created_at` timestamps with `status=pending` (indicates stuck job)
- Multiple notifications with `has_delivery_error=true` (indicates systematic issue)

---

## Troubleshooting

### Users Not Receiving Emails

**Check notification preferences:**

```bash
curl -X GET "http://localhost:5000/api/user/notification-preferences" \
  -H "Authorization: Bearer <token>"
```

Confirm the relevant preference field is `true` for the event type.

**Check admin notification list:**

```bash
curl -X GET "http://localhost:5000/api/admin/notifications?limit=100" \
  -H "Authorization: Bearer <token>" \
  | jq '.notifications[] | select(.recipient_id == USER_ID)'
```

Look for:

- `status=pending`: Notification waiting to be processed by cron job
- `status=failed_permanently`: Max retries exceeded, check RESEND_API_KEY
- `status=sent` with old `sent_at`: Notification sent successfully (check spam folder)
- `has_delivery_error=true`: Transient error, should retry automatically

**Verify RESEND_API_KEY:**

Test Resend connectivity:

```bash
curl -X POST "https://api.resend.com/emails" \
  -H "Authorization: Bearer $RESEND_API_KEY" \
  -d '{"from":"test@example.com","to":"user@example.com","subject":"Test","html":"<p>Test</p>"}'
```

### Cron Job Not Running

Confirm the background job is scheduled:

```bash
# Check cron entries
crontab -l | grep process_notifications

# Expected entry: * * * * * /path/to/uv run scripts/process_notifications.py
```

If missing, add to crontab:

```bash
# Run every minute
* * * * * cd /path/to/monorepo && uv run scripts/process_notifications.py >> /tmp/notifications.log 2>&1
```

Check job output:

```bash
tail -f /tmp/notifications.log
```

### Invalid Unsubscribe Tokens

**Verify UNSUBSCRIBE_SECRET is set:**

```bash
echo $UNSUBSCRIBE_SECRET  # Should not be empty
```

**Generate a valid token for testing:**

```python
import hmac

user_id = 42
secret = os.environ["UNSUBSCRIBE_SECRET"]
token = hmac.new(secret.encode(), f"{user_id}".encode(), "sha256").hexdigest()
print(f"/api/unsubscribe?user_id={user_id}&token={token}")
```

**Test the unsubscribe endpoint:**

```bash
curl -X GET "http://localhost:5000/api/unsubscribe?user_id=42&token=<generated_token>"
```

---

## Testing Examples

### Using curl

#### Get User Preferences

```bash
TOKEN="<your_jwt_token>"
curl -X GET "http://localhost:5000/api/user/notification-preferences" \
  -H "Authorization: Bearer $TOKEN"
```

#### Update Preferences (Disable Mentions)

```bash
curl -X PUT "http://localhost:5000/api/user/notification-preferences" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"notify_on_mentions": false}'
```

#### List Admin Notifications

```bash
curl -X GET "http://localhost:5000/api/admin/notifications?skip=0&limit=20" \
  -H "Authorization: Bearer $TOKEN"
```

#### Unsubscribe via Token

```bash
UNSUBSCRIBE_TOKEN="<generated_token>"
curl -X GET "http://localhost:5000/api/unsubscribe?user_id=42&token=$UNSUBSCRIBE_TOKEN"
```

### Using Python Requests

```python
import requests

BASE_URL = "http://localhost:5000"
TOKEN = "<your_jwt_token>"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


def get_preferences() -> dict:
    """Get user notification preferences."""
    response = requests.get(
        f"{BASE_URL}/api/user/notification-preferences",
        headers=HEADERS,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def update_preferences(notify_on_mentions: bool) -> dict:
    """Update a single preference."""
    response = requests.put(
        f"{BASE_URL}/api/user/notification-preferences",
        json={"notify_on_mentions": notify_on_mentions},
        headers=HEADERS,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def list_admin_notifications(skip: int = 0, limit: int = 50) -> dict:
    """List notifications for admin monitoring."""
    response = requests.get(
        f"{BASE_URL}/api/admin/notifications",
        params={"skip": skip, "limit": limit},
        headers=HEADERS,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def unsubscribe_user(user_id: int, token: str) -> dict:
    """Unsubscribe from all notifications."""
    response = requests.get(
        f"{BASE_URL}/api/unsubscribe",
        params={"user_id": user_id, "token": token},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()
```

---

## Error Codes Reference

| HTTP Status | Meaning               | Typical Cause                                     |
| :---------- | :-------------------- | :------------------------------------------------ |
| 200         | Success               | Operation completed successfully                  |
| 400         | Bad Request           | Invalid query params, missing body, invalid token |
| 401         | Unauthorized          | Missing or expired JWT token                      |
| 403         | Forbidden             | Valid token but insufficient permissions (admin)  |
| 500         | Internal Server Error | Unexpected server error or configuration issue    |
