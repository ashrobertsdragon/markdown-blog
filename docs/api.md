# API Documentation

## Health Check Endpoints

### Introduction

Health check endpoints are critical monitoring interfaces that allow operators, monitoring systems, and deployment pipelines to verify the health and operational status of the blog platform. These endpoints provide visibility into three key areas:

1. **Application Uptime** - Verify the Flask application is running and responsive
1. **Database Connectivity** - Confirm the PostgreSQL database is accessible and operational
1. **External API Reachability** - Monitor GitHub API connectivity for version control integration

Health checks are designed to be lightweight, fast (typically under 100ms), and capable of being called frequently by automated monitoring systems without impacting application performance.

---

## Endpoint: GET /health

### Purpose

Perform a basic application uptime check. This endpoint confirms that the Flask application is running and responding to requests. This is the most lightweight health check and should succeed as long as the application process is running.

### HTTP Method and URL

```text
GET /health
```

### Request Format

No request parameters, headers, or body required.

```bash
curl -X GET http://localhost:5000/health
```

### Response Format

**JSON Schema:**

```json
{
  "type": "object",
  "properties": {
    "status": {
      "type": "string",
      "enum": ["healthy"],
      "description": "Application health status"
    }
  },
  "required": ["status"]
}
```

### Success Response (200 OK)

**HTTP Status Code:** `200 OK`

**Response Body:**

```json
{
  "status": "healthy"
}
```

**Headers:**

```text
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 21
```

### Use Cases

- **Kubernetes Liveness Probe** - Configure as liveness probe to restart failed containers
- **Load Balancer Health Check** - Verify backend instance availability
- **Uptime Monitoring Services** - Services like Pingdom or Uptime Robot use this to track application availability
- **Deployment Verification** - Verify successful deployment before routing traffic
- **Manual Health Inspection** - Quick check that the application is responsive

### Performance Characteristics

- **Response Time:** < 10ms (typically 1-5ms)
- **Resource Usage:** Minimal (no database queries)
- **Failure Rate:** Should be 0% when application is running

---

## Endpoint: GET /health/db

### Purpose

Verify database connectivity and confirm the PostgreSQL database is accessible and operational. This endpoint executes a simple test query (`SELECT 1`) to validate the connection pool and database responsiveness.

### HTTP Method and URL

```text
GET /health/db
```

### Request Format

No request parameters, headers, or body required.

```bash
curl -X GET http://localhost:5000/health/db
```

### Response Format

**JSON Schema (Success):**

```json
{
  "type": "object",
  "properties": {
    "status": {
      "type": "string",
      "enum": ["healthy"],
      "description": "Database health status"
    },
    "database": {
      "type": "string",
      "description": "Database name"
    },
    "host": {
      "type": "string",
      "description": "Database hostname or IP address"
    }
  },
  "required": ["status"]
}
```

**JSON Schema (Error):**

```json
{
  "type": "object",
  "properties": {
    "status": {
      "type": "string",
      "enum": ["unhealthy"],
      "description": "Database health status"
    },
    "error": {
      "type": "string",
      "description": "Error message explaining the failure"
    }
  },
  "required": ["status", "error"]
}
```

### Success Response (200 OK)

**HTTP Status Code:** `200 OK`

{
  "status": "healthy",
  "database": "connected"
}

**Headers:**

```text
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 61
```

### Error Response (503 Service Unavailable)

**HTTP Status Code:** `503 Service Unavailable`

**Response Body:**

```json
{
  "status": "unhealthy",
  "database": "unreachable"
}
```

**Headers:**

```text
HTTP/1.1 503 Service Unavailable
Content-Type: application/json
Content-Length: 95
Retry-After: 30
```

### Use Cases

- **Database Deployment Validation** - Confirm database is ready before marking deployment successful
- **Connection Pool Monitoring** - Detect database connectivity issues in production
- **Automated Alerts** - Trigger alerts when database becomes inaccessible
- **Readiness Probe** - Kubernetes readiness probe to prevent routing traffic before database is ready
- **CI/CD Pipeline Checks** - Verify database setup in test environments before running integration tests

### Performance Characteristics

- **Response Time:** 50-100ms (typically 75ms)
- **Resource Usage:** One database connection from pool
- **Failure Scenarios:** Connection refused, authentication error, timeout, database offline

### Implementation Details

The endpoint executes a minimal test query:

```sql
SELECT 1
```

This query:

- Requires no table access (pure database test)
- Executes immediately on any PostgreSQL version
- Validates the connection is functional
- Returns in < 1ms on healthy database

---

## Endpoint: GET /health/github

### Purpose

Verify connectivity to the GitHub API and confirm rate limit status. This endpoint makes a request to the GitHub API to validate that external service connectivity is functional. This is essential since the platform uses GitHub to back up draft revisions.

### HTTP Method and URL

```text
GET /health/github
```

### Request Format

No request parameters, headers, or body required.

```bash
curl -X GET http://localhost:5000/health/github
```

### Response Format

**JSON Schema (Success):**

```json
{
  "type": "object",
  "properties": {
    "status": {
      "type": "string",
      "enum": ["healthy"],
      "description": "GitHub API health status"
    },
    "rate_limit": {
      "type": "object",
      "properties": {
        "limit": {
          "type": "integer",
          "description": "Total API requests allowed per hour"
        },
        "remaining": {
          "type": "integer",
          "description": "API requests remaining in current window"
        },
        "reset": {
          "type": "integer",
          "description": "Unix timestamp when rate limit resets"
        }
      },
      "required": ["limit", "remaining", "reset"]
    }
  },
  "required": ["status", "rate_limit"]
}
```

**JSON Schema (Error):**

```json
{
  "type": "object",
  "properties": {
    "status": {
      "type": "string",
      "enum": ["unhealthy"],
      "description": "GitHub API health status"
    },
    "error": {
      "type": "string",
      "description": "Error message explaining the failure"
    }
  },
  "required": ["status", "error"]
}
```

### Success Response (200 OK)

**HTTP Status Code:** `200 OK`

```json
{
  "status": "healthy",
  "github": "reachable"
}
```

**Headers:**

```text
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 103
X-RateLimit-Limit: 5000
X-RateLimit-Remaining: 4987
X-RateLimit-Reset: 1703001600
```

### Error Response (503 Service Unavailable)

**HTTP Status Code:** `503 Service Unavailable`

**Response Body:**

```json
{
  "status": "unhealthy",
  "github": "unreachable"
}
```

**Headers:**

```text
HTTP/1.1 503 Service Unavailable
Content-Type: application/json
Content-Length: 125
Retry-After: 60
```

### Use Cases

- **Backup System Verification** - Confirm GitHub integration is operational before allowing draft creation
- **Rate Limit Monitoring** - Track API quota consumption to prevent hitting limits
- **External Service Status** - Detect GitHub outages affecting backup operations
- **Degraded Mode Handling** - Prompt application to use local-only mode if GitHub is unavailable
- **Alerting Systems** - Notify operators when GitHub connectivity is impaired
- **Deployment Health Checks** - Verify external dependencies are accessible before marking deployment complete

### Performance Characteristics

- **Response Time:** 200-500ms (typically 300ms)
- **Resource Usage:** One outbound HTTP request to GitHub API
- **Failure Scenarios:** Network timeout, rate limit exceeded, authentication error, GitHub API error
- **Rate Limit Impact:** Consumes 1 API request per call (limit is 5000/hour for authenticated requests)

### Implementation Details

The endpoint queries the GitHub API rate limit endpoint:

```text
GET https://api.github.com/rate_limit
```

This endpoint:

- Requires authentication via `GITHUB_TOKEN` environment variable
- Returns current rate limit status without consuming a request (special behavior)
- Indicates overall API health and quota availability
- Validates network connectivity to GitHub infrastructure

### Rate Limiting

**Important:** The `/health/github` endpoint should not be called more frequently than every 60 seconds in production. More frequent calls will:

- Consume API quota unnecessarily
- Impact performance due to network latency
- Provide redundant information (rate limits change hourly)

**Recommended Monitoring Strategy:**

- Call every 5-10 minutes for automated monitoring
- Call on-demand for troubleshooting
- Use application-level caching of results (max 60 seconds)

---

## Error Codes and Status Meanings

### HTTP Status Codes

| Status Code                   | Meaning                                    | Cause                                                        | Recovery                                                                        |
| ----------------------------- | ------------------------------------------ | ------------------------------------------------------------ | ------------------------------------------------------------------------------- |
| **200 OK**                    | Endpoint responding successfully           | Application is operational                                   | N/A (healthy)                                                                   |
| **503 Service Unavailable**   | Dependency is inaccessible or unresponsive | Database/GitHub unreachable, timeout, authentication failure | Fix underlying issue (restart service, check credentials, restore connectivity) |
| **500 Internal Server Error** | Unexpected error in health check logic     | Bug in endpoint implementation                               | Contact developers, review logs                                                 |
| **404 Not Found**             | Endpoint does not exist                    | Typo in URL or endpoint not deployed                         | Verify endpoint URL, check deployment status                                    |

### Failure Causes and Resolution

#### `/health` Failures

| Symptom            | Cause                   | Resolution                                         |
| ------------------ | ----------------------- | -------------------------------------------------- |
| Connection refused | Flask app not running   | Check Flask process, restart application           |
| Timeout            | Flask app hung/blocking | Restart application, check for resource exhaustion |
| 404 Not Found      | Endpoint not registered | Check Flask blueprint registration, redeploy       |

#### `/health/db` Failures

| Symptom                       | Cause                               | Resolution                                           |
| ----------------------------- | ----------------------------------- | ---------------------------------------------------- |
| "connection refused"          | PostgreSQL not running              | Start PostgreSQL service                             |
| "invalid credentials"         | Wrong database user/password        | Verify DB_USER and DB_PASSWORD environment variables |
| "database does not exist"     | Database not created                | Run database initialization script                   |
| "connection timeout"          | Connection pool exhausted           | Increase pool size, restart application              |
| "Ident authentication failed" | PostgreSQL local auth issue (Linux) | Configure pg_hba.conf, use password auth             |

#### `/health/github` Failures

| Symptom                     | Cause                            | Resolution                                                          |
| --------------------------- | -------------------------------- | ------------------------------------------------------------------- |
| "connection timeout"        | Network unreachable to GitHub    | Check firewall rules, verify internet connectivity                  |
| "rate limit exceeded"       | Too many API calls               | Wait for rate limit window to reset (hourly), reduce call frequency |
| "invalid token"             | GITHUB_TOKEN missing or expired  | Set GITHUB_TOKEN environment variable, regenerate token             |
| "connection refused"        | Network firewall blocking GitHub | Configure firewall whitelist, check outbound rules                  |
| "500 Internal Server Error" | GitHub API outage                | Wait for GitHub to recover, check GitHub status page                |

---

## Testing Examples

### Using curl

#### Test Basic Health

```bash
curl -X GET http://localhost:5000/health
```

**Expected Output:**

```json
{
  "status": "healthy"
}
```

#### Test Database Health

```bash
curl -X GET http://localhost:5000/health/db
```

**Expected Output:**

```json
{
  "status": "healthy",
  "database": "blog_db",
  "host": "localhost"
}
```

#### Test GitHub Health

```bash
curl -X GET http://localhost:5000/health/github
```

**Expected Output:**

```json
{
  "status": "healthy",
  "rate_limit": {
    "limit": 5000,
    "remaining": 4987,
    "reset": 1703001600
  }
}
```

### Using Bash Script for All Health Checks

```bash
#!/bin/bash

BASE_URL="http://localhost:5000"
TIMEOUT=10

echo "Checking application health..."
APP_RESPONSE=$(curl -s -w "\n%{http_code}" -m $TIMEOUT "$BASE_URL/health")
APP_STATUS=$(echo "$APP_RESPONSE" | tail -1)
APP_BODY=$(echo "$APP_RESPONSE" | head -1)

echo "Application: $APP_STATUS"
[ "$APP_STATUS" = "200" ] && echo "✓ App healthy" || echo "✗ App unhealthy"
echo "$APP_BODY" | jq .

echo ""
echo "Checking database health..."
DB_RESPONSE=$(curl -s -w "\n%{http_code}" -m $TIMEOUT "$BASE_URL/health/db")
DB_STATUS=$(echo "$DB_RESPONSE" | tail -1)
DB_BODY=$(echo "$DB_RESPONSE" | head -1)

echo "Database: $DB_STATUS"
[ "$DB_STATUS" = "200" ] && echo "✓ Database healthy" || echo "✗ Database unhealthy"
echo "$DB_BODY" | jq .

echo ""
echo "Checking GitHub health..."
GH_RESPONSE=$(curl -s -w "\n%{http_code}" -m $TIMEOUT "$BASE_URL/health/github")
GH_STATUS=$(echo "$GH_RESPONSE" | tail -1)
GH_BODY=$(echo "$GH_RESPONSE" | head -1)

echo "GitHub: $GH_STATUS"
[ "$GH_STATUS" = "200" ] && echo "✓ GitHub healthy" || echo "✗ GitHub unhealthy"
echo "$GH_BODY" | jq .
```

### Using Python Requests

```python
import requests
import json

BASE_URL = "http://localhost:5000"


def check_health():
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        print(f"App Health: {response.status_code}")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"App Health Failed: {e}")


def check_database():
    try:
        response = requests.get(f"{BASE_URL}/health/db", timeout=10)
        print(f"Database Health: {response.status_code}")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Database Health Failed: {e}")


def check_github():
    try:
        response = requests.get(f"{BASE_URL}/health/github", timeout=10)
        print(f"GitHub Health: {response.status_code}")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"GitHub Health Failed: {e}")


if __name__ == "__main__":
    check_health()
    print()
    check_database()
    print()
    check_github()
```

### Using Kubernetes

#### Liveness Probe Configuration

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: blog-app
spec:
  containers:
    - name: blog
      image: blog-app:latest
      livenessProbe:
        httpGet:
          path: /health
          port: 5000
        initialDelaySeconds: 10
        periodSeconds: 30
        timeoutSeconds: 5
        failureThreshold: 3
```

#### Readiness Probe Configuration

```yaml
readinessProbe:
  httpGet:
    path: /health/db
    port: 5000
  initialDelaySeconds: 20
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
```

### Using Monitoring Systems

#### Prometheus Configuration

```yaml
global:
  scrape_interval: 30s

scrape_configs:
  - job_name: 'blog-app'
    static_configs:
      - targets: ['localhost:5000']
    metrics_path: '/health'
```

#### Datadog Configuration

```python
from datadog import initialize, api

options = {"api_key": "YOUR_API_KEY", "app_key": "YOUR_APP_KEY"}

initialize(**options)

monitor = {
    "type": "http_check",
    "query": "http://localhost:5000/health",
    "name": "Blog App Health Check",
    "message": "Alert if health check fails",
    "tags": ["blog", "production"],
}

api.Monitor.create(**monitor)
```

### Using Postman

1. Create a new request with method `GET`
1. Enter URL: `http://localhost:5000/health/db`
1. Set timeout to 10000ms
1. Add header: `Accept: application/json`
1. Click "Send" to test
1. Verify response status is 200
1. Verify response body contains `"status": "healthy"`

---

## Monitoring Best Practices

### Recommended Monitoring Strategy

1. **Application Health (`/health`)**

   - Call every 10-30 seconds
   - Low priority alerting (may indicate capacity issues only)
   - Consider as "heartbeat" check

1. **Database Health (`/health/db`)**

   - Call every 30-60 seconds
   - High priority alerting (blocks all application functionality)
   - Use as deployment readiness gate

1. **GitHub Health (`/health/github`)**

   - Call every 5-10 minutes
   - Medium priority alerting (blocks backup/versioning features)
   - Monitor rate limit to prevent quota exhaustion

### Alert Thresholds

- **Failure Count:** Alert after 2 consecutive failures (30-60 seconds down)
- **Response Time:** Alert if response time exceeds 5 seconds
- **Rate Limit:** Alert when remaining requests drop below 10% of limit
- **Database Timeout:** Alert immediately on timeout

### Logging and Metrics

Each health check endpoint logs:

- Request timestamp
- Response status
- Response time
- Error details (if applicable)
- Rate limit headers (for GitHub health)

Example log entry:

```text
2023-12-20T10:30:45.123Z [INFO] health.py - GET /health - status=healthy - duration=2.34ms
2023-12-20T10:30:50.456Z [INFO] health.py - GET /health/db - status=healthy - duration=75.67ms
2023-12-20T10:30:55.789Z [WARN] health.py - GET /health/github - rate_limit_remaining=98 - duration=312.45ms
```
