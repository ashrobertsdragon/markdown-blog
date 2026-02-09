# Flask + React Blog Platform

A modern blog platform combining Domain-Driven Design principles with a dual-storage architecture. Draft posts exist as version-controlled markdown files synced to GitHub, while published content is cached in PostgreSQL for high performance.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)

## Overview

### Key Features

- **Dual Storage**: Markdown drafts on the filesystem with GitHub sync; published HTML in PostgreSQL.
- **Domain-Driven Design**: Organized into 5 bounded contexts (Content, Version Control, Discussion, Notification, Identity).
- **Hexagonal Architecture**: A clean separation between domain logic and infrastructure.
- **Real-time Version Control**: Every save commits to the GitHub API for a complete revision history.
- **Test-Driven Development**: High test coverage with a comprehensive test pyramid.
- **Modern Stack**: Flask, React, TypeScript, Tailwind CSS, and Clerk for authentication.

### Tech Stack

| Layer               | Technology                   | Purpose                                |
| :------------------ | :--------------------------- | :------------------------------------- |
| **Frontend**        | React 18 + Vite              | UI framework and build tool            |
| **Styling**         | Tailwind CSS                 | Utility-first styling                  |
| **Backend**         | Flask 3.0+                   | REST API server                        |
| **Language**        | Python 3.13                  | Backend runtime                        |
| **Database**        | PostgreSQL                   | Persistent storage for published posts |
| **Storage**         | Filesystem + GitHub          | Draft markdown version control         |
| **Auth**            | Clerk                        | Authentication and user management     |
| **Email**           | Resend                       | Transactional emails                   |
| **Package Manager** | uv                           | Fast Python dependency resolver        |
| **Linting**         | Ruff + Biome                 | Code quality enforcement               |
| **Testing**         | pytest + Vitest + Playwright | Test automation                        |

## Quick Start

### Prerequisites

- **Python 3.13+**
- **Node.js 22.18+ or 24.6+**
- **PostgreSQL 10.23+**
- **uv** (Python package manager): `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Git**

### Local Development Setup

1. **Clone the Repository**

   ```bash
   git clone https://github.com/ashrobertsdragon/markdown-blog
   cd markdown-blog
   ```

1. **Configure Environment**

   - Copy `backend/.env.example` to `backend/.env`.
   - Copy `frontend/.env.example` to `frontend/.env`.
   - Fill in the required values in both `.env` files, such as database credentials and API keys.

1. **Setup Backend**

   ```bash
   cd backend
   uv sync
   ```

1. **Setup Frontend**

   ```bash
   cd ../frontend
   npm install
   ```

1. **Setup Database**
   Ensure your PostgreSQL server is running, then create the development database.

   ```bash
   createdb blog_dev
   ```

   The backend is configured to use this database via the `DATABASE_URL` in `backend/.env`.

1. **Run the Application**
   Open two terminals:

   ```bash
   # Terminal 1: Start the Backend with entrypoint script (from backend/)
   uv run dev_flask

   # Terminal 2: Start the Frontend (from frontend/)
   npm run dev
   ```

   - The backend API will be available at `http://localhost:5000`.
   - The frontend will be available at `http://localhost:5173`.

## Development

### Project Structure

```plaintext
monorepo/
├── backend/                      # Flask API (Python 3.13)
│   ├── src/
│   │   ├── passenger_wsgi.py    # Production WSGI entry
│   │   ├── scripts/             # Cron jobs (notifications, sync, cleanup)
│   │   └── backend/
│   │       ├── main.py          # Flask app factory
│   │       ├── config.py        # Environment configuration
│   │       ├── domain/          # Business logic (aggregates, value objects, events)
│   │       ├── application/     # Use cases (commands, queries, handlers)
│   │       ├── infrastructure/  # External adapters (DB, GitHub, email, auth)
│   │       └── api/             # HTTP layer (routes, middleware)
│   ├── tests/                   # Test suite (unit, integration, e2e)
│   ├── pyproject.toml           # uv project definition
│   └── uv.lock                  # Dependency lockfile
├── frontend/                     # React SPA (Node.js 22+)
│   ├── src/
│   │   ├── components/          # Reusable UI (post, comment, admin, common)
│   │   ├── pages/               # Route pages (Home, PostPage, AdminPage)
│   │   ├── hooks/               # Custom hooks (useAuth, usePostMutation)
│   │   ├── services/            # API clients (postService, commentService)
│   │   ├── context/             # React context (AuthContext)
│   │   ├── App.jsx              # Root component
│   │   └── main.jsx             # Vite entry point
│   ├── tests/                   # Vitest unit + Playwright e2e
│   ├── package.json             # npm dependencies
│   ├── vite.config.js           # Vite configuration
│   ├── biome.json               # Linter/formatter config
│   └── tailwind.config.js       # Tailwind CSS config
├── shared/
│   └── openapi.yaml             # API contract specification
├── .github/workflows/           # CI/CD (backend-ci.yml, frontend-ci.yml)
├── .pre-commit-config.yaml      # Pre-commit hooks
└── README.md                    # This file
```

### Environment Variables

#### Backend (.env)

```bash
# Database (for development)
LOCAL_DB_HOST=localhost
LOCAL_DB_NAME=blog_dev
LOCAL_DB_USER=your_user
LOCAL_DB_PASSWORD=your_password

# GitHub API (for draft sync)
GITHUB_TOKEN=your_github_personal_access_token
GITHUB_REPO_OWNER=yourusername
GITHUB_REPO_NAME=blog-drafts

# Resend (email notifications)
RESEND_API_KEY=re_your_resend_api_key
NOTIFICATION_FROM_EMAIL=notifications@yourdomain.com

# Clerk (authentication)
CLERK_SECRET_KEY=sk_test_your_clerk_secret_key

# Flask
FLASK_ENV=development
FLASK_DEBUG=1
SECRET_KEY=your_secret_key_for_sessions
```

#### Frontend (.env)

```bash
# API Configuration
VITE_API_BASE_URL=http://localhost:5000

# Clerk (authentication)
VITE_CLERK_PUBLISHABLE_KEY=pk_test_your_clerk_publishable_key
```

### Common Commands

#### Backend (Python + uv)

````bash
cd backend

# Install/update dependencies
uv sync

# Run Flask development server with entrypoint
uv run dev_flask

# Code quality
uvx ruff check --fix .           # Lint and auto-fix
uvx ruff format .                # Format code
uv run mypy src/                 # Type checking with mypy
uvx ty check                     # Type checking with ty (faster alternative)

**CRITICAL**: Always use `uv run` to execute Python commands to ensure the correct virtual environment is used.

#### Frontend (React + Vite)

```bash
./scripts/build.sh
````

## Authentication

### Overview

The blog platform uses **Clerk** for authentication and role-based access control (RBAC). Clerk provides JWT-based authentication with RS256 signature validation, while the backend enforces role-based authorization through custom middleware decorators.

**Key Features:**

- **JWT Authentication**: Clerk-issued tokens validated on every protected request
- **Role Hierarchy**: Three roles with hierarchical permissions (authenticated < author < admin)
- **Automatic User Provisioning**: Users created in local database on first login
- **Decorator-Based Protection**: Simple `@require_auth` and `@require_role` decorators
- **React Integration**: ClerkProvider + custom `useAuth` hook for seamless frontend auth

### Backend Configuration

#### Environment Variables

Add these to `backend/.env`:

```bash
CLERK_SECRET_KEY=sk_test_your_clerk_secret_key
CLERK_PUBLISHABLE_KEY=pk_test_your_clerk_publishable_key
```

**Where to find these values:**

1. Sign up at [clerk.com](https://clerk.com)
1. Create a new application
1. Navigate to **API Keys** in the Clerk dashboard
1. Copy the **Secret Key** and **Publishable Key**

#### Protecting Endpoints

Use middleware decorators to protect Flask routes:

##### Example: Require authentication

```python
from flask import Blueprint, g, jsonify
from backend.api.middleware.auth_middleware import require_auth

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/me", methods=["GET"])
@require_auth
def get_current_user():
    user = g.current_user
    return jsonify(user.to_dict()), 200
```

##### Example: Require specific role

```python
from flask import Blueprint, jsonify
from backend.api.middleware.auth_middleware import require_auth, require_role

posts_bp = Blueprint("posts", __name__)


@posts_bp.route("", methods=["POST"])
@require_auth
@require_role("author")
def create_post():
    return jsonify({"message": "Post created"}), 201


@posts_bp.route("/admin/settings", methods=["PUT"])
@require_auth
@require_role("admin")
def update_settings():
    return jsonify({"message": "Settings updated"}), 200
```

**Important**: Always use `@require_auth` before `@require_role`. The `@require_role` decorator depends on `g.current_user` being set by `@require_auth`.

Correct usage:

```python
@posts_bp.route("/posts", methods=["POST"])
@require_auth  # Required first
@require_role("author")  # Then check role
def create_post(): ...
```

Incorrect usage (will fail):

```python
@posts_bp.route("/posts", methods=["POST"])
@require_role("author")  # Wrong - g.current_user not set yet
def create_post(): ...
```

##### Accessing current user

The `@require_auth` decorator injects the authenticated user into Flask's `g.current_user`:

```python
from flask import g, jsonify
from backend.api.middleware.auth_middleware import require_auth, require_role


@posts_bp.route("/<int:user_id>/role", methods=["PUT"])
@require_auth
@require_role("admin")
def update_user_role(user_id: int):
    admin_user = g.current_user

    user = user_repo.find_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    user.change_role(new_role)
    updated_user = user_repo.save(user)

    return jsonify({"user": updated_user.to_dict()}), 200
```

**Role Hierarchy:**

- **authenticated**: Base role for any signed-in user
- **author**: Can create and edit posts (includes all authenticated permissions)
- **admin**: Full system access (includes all author permissions)

#### Error Responses

**401 Unauthorized** - Authentication failures:

| Error Message                         | Cause                                           | HTTP Status |
| ------------------------------------- | ----------------------------------------------- | ----------- |
| "Missing authorization header"        | No Authorization header in request              | 401         |
| "Invalid authorization header format" | Header doesn't start with "Bearer "             | 401         |
| "Empty token"                         | Authorization header is "Bearer " with no token | 401         |
| "Token verification failed"           | JWT signature invalid or expired                | 401         |
| "User not authenticated"              | `@require_role` used without `@require_auth`    | 401         |

**403 Forbidden** - Insufficient permissions:

```json
{
  "error": "Author role required",
  "required_role": "author"
}
```

or

```json
{
  "error": "Admin role required",
  "required_role": "admin"
}
```

### Frontend Configuration

#### Environment Variables

Add to `frontend/.env`:

```bash
VITE_CLERK_PUBLISHABLE_KEY=pk_test_your_clerk_publishable_key
```

Use the same publishable key from the Clerk dashboard.

#### Clerk Provider Setup

The application wraps the entire React tree with `ClerkProvider` and `AuthProvider` in `main.tsx`. This provides authentication state to all components through React context.

The `ClerkProvider` handles Clerk's authentication flow, while `AuthProvider` extends it with role-based logic and a custom `useAuth` hook.

#### Using Authentication in Components

##### useAuth Hook

Access authentication state and user information:

```tsx
import { useAuth } from "@/context/AuthContext";

function ProfilePage() {
  const { user, isLoaded, isSignedIn, role } = useAuth();

  if (!isLoaded) {
    return <div>Loading...</div>;
  }

  if (!isSignedIn) {
    return <div>Please sign in</div>;
  }

  return (
    <div>
      <h1>Welcome, {user?.firstName}</h1>
      <p>Email: {user?.emailAddresses[0]?.emailAddress}</p>
      <p>Role: {role}</p>
    </div>
  );
}
```

**Note**: The `user` object is a Clerk `UserResource` type with properties like `firstName`, `lastName`, `emailAddresses`, etc. See [Clerk User documentation](https://clerk.com/docs/references/javascript/user/user) for the full API reference.

##### Protected Routes

Protect entire routes with the `ProtectedRoute` component:

```tsx
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import AdminDashboard from "@/pages/AdminDashboard";
import CreatePost from "@/pages/CreatePost";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />

        <Route
          path="/create-post"
          element={
            <ProtectedRoute requireRole="author">
              <CreatePost />
            </ProtectedRoute>
          }
        />

        <Route
          path="/admin"
          element={
            <ProtectedRoute requireRole="admin">
              <AdminDashboard />
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
```

##### Conditional Rendering by Role

Show/hide UI elements based on user role:

```tsx
import { useAuth } from "@/context/AuthContext";

function PostActions({ postId }: { postId: number }) {
  const { role } = useAuth();

  return (
    <div>
      {role === "author" || role === "admin" ? (
        <button onClick={() => editPost(postId)}>Edit Post</button>
      ) : null}

      {role === "admin" ? (
        <button onClick={() => deletePost(postId)}>Delete Post</button>
      ) : null}
    </div>
  );
}
```

#### Authentication Hooks

The application provides two `useAuth` hooks with different purposes:

1. **Custom useAuth** (`@/context/AuthContext`):

   - Provides role-based logic (`role`, `isSignedIn`, `isLoaded`, `user`)
   - Use for role checks and user display in components

1. **Clerk useAuth** (`@clerk/clerk-react`):

   - Provides `getToken()` for obtaining JWT tokens
   - Use when making authenticated API calls

**Example combining both**:

```tsx
import { useAuth as useClerkAuth } from "@clerk/clerk-react";
import { useAuth } from "@/context/AuthContext";

function CreatePostButton() {
  const { role, isSignedIn } = useAuth();           // Custom hook for role
  const { getToken } = useClerkAuth();              // Clerk hook for token

  if (!isSignedIn || role !== "author") {
    return null;
  }

  const handleClick = async () => {
    const token = await getToken();
    const response = await fetch("/api/posts", {
      headers: { "Authorization": `Bearer ${token}` }
    });
  };

  return <button onClick={handleClick}>Create Post</button>;
}
```

### Common Patterns

#### Pattern 1: Author-only API call with error handling

```tsx
import { useAuth as useClerkAuth } from "@clerk/clerk-react";
import { useAuth } from "@/context/AuthContext";

function CreatePostButton() {
  const { user, isSignedIn, role } = useAuth();     // Custom hook
  const { getToken } = useClerkAuth();              // Clerk hook for token

  const handleCreatePost = async () => {
    if (!isSignedIn || role !== "author") return;

    try {
      const token = await getToken();              // Now properly imported
      const response = await fetch("/api/posts", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`        // Using token from Clerk
        },
        body: JSON.stringify({ title: "New Post", content: "..." })
      });

      if (!response.ok) throw new Error("Failed to create post");

      const data = await response.json();
      console.log("Post created:", data);
    } catch (error) {
      console.error("Error creating post:", error);
    }
  };

  if (!isSignedIn || role !== "author") return null;

  return <button onClick={handleCreatePost}>Create Post</button>;
}
```

#### Pattern 2: Admin dashboard with role check

```tsx
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { useAuth } from "@/context/AuthContext";

function AdminDashboard() {
  const { user, role } = useAuth();

  return (
    <div>
      <h1>Admin Dashboard</h1>
      <p>Logged in as {user?.emailAddresses[0]?.emailAddress}</p>
      <p>Role: {role}</p>

      <UserManagement />
      <PostModeration />
    </div>
  );
}

function AdminRoute() {
  return (
    <ProtectedRoute requireRole="admin">
      <AdminDashboard />
    </ProtectedRoute>
  );
}
```

#### Pattern 3: Backend endpoint with user context

```python
from flask import Blueprint, g, jsonify, request
from backend.api.middleware.auth_middleware import require_auth, require_role

posts_bp = Blueprint("posts", __name__)


@posts_bp.route("", methods=["POST"])
@require_auth
@require_role("author")
def create_post():
    author = g.current_user

    data = request.get_json()
    post = Post(
        title=data["title"],
        content=data["content"],
        author_id=author.id,
        author_email=author.email,
    )

    post_repo.save(post)

    return jsonify({"post": post.to_dict(), "created_by": author.email}), 201
```

### Troubleshooting

| Problem                                      | Cause                                                        | Solution                                                                                                                        |
| :------------------------------------------- | :----------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------ |
| **401: Missing authorization header**        | Frontend not sending JWT token                               | Ensure `Authorization: Bearer <token>` header is included in API requests. Use Clerk's `getToken()` method to retrieve the JWT. |
| **401: Invalid authorization header format** | Malformed Authorization header                               | Format must be `Authorization: Bearer <token>` with exactly one space after "Bearer".                                           |
| **401: Token verification failed**           | Invalid JWT signature or expired token                       | Check that `CLERK_SECRET_KEY` matches your Clerk dashboard. Token may be expired; Clerk automatically refreshes tokens.         |
| **403: Author role required**                | User has `authenticated` role but endpoint requires `author` | Update user role in database via admin endpoint: `PUT /users/<id>/role` with `{"role": "author"}`.                              |
| **403: Admin role required**                 | User lacks admin permissions                                 | Only admins can access admin endpoints. Update role to `admin` via database or admin API.                                       |
| **useAuth must be used within AuthProvider** | Component not wrapped in AuthProvider                        | Ensure `main.tsx` wraps app with `<ClerkProvider>` and `<AuthProvider>`.                                                        |
| **Environment variable undefined**           | `.env` file not loaded                                       | Verify `.env` exists in `backend/` and `frontend/` directories. Restart dev servers after updating `.env`.                      |
| **CORS error on auth endpoints**             | Backend CORS not configured                                  | Ensure `CORS(app)` is configured in `backend/src/backend/main.py` with appropriate origins.                                     |

**Debugging Tips:**

1. **Check JWT payload**: Use [jwt.io](https://jwt.io) to decode tokens and verify claims (`sub`, `email`, `exp`)
1. **Inspect network requests**: Use browser DevTools Network tab to verify `Authorization` header is present
1. **Enable Flask debug logging**: Set `FLASK_DEBUG=1` in `backend/.env` to see detailed auth errors
1. **Test with curl**: Manually test endpoints with curl to isolate frontend vs backend issues:

```bash
# Get token from Clerk dashboard or browser DevTools
TOKEN="your_jwt_token_here"

# Test authentication
curl -H "Authorization: Bearer $TOKEN" http://localhost:5000/auth/me

# Test role-based access
curl -H "Authorization: Bearer $TOKEN" http://localhost:5000/users
```

## Post Management

### API Endpoints

The post management API provides endpoints for creating, editing, publishing, and listing blog posts. All endpoints require authentication.

#### Create Draft

Create a new blog post draft.

**Endpoint:** `POST /api/posts`

**Authentication:** Required (author role minimum)

**Request body:**

```json
{
  "slug": "my-first-post",
  "title": "My First Blog Post"
}
```

**Response (201 Created):**

```json
{
  "id": 1,
  "slug": "my-first-post",
  "title": "My First Blog Post",
  "author_id": 42,
  "html_content": null,
  "published": false,
  "published_at": null,
  "created_at": "2026-01-20T14:30:00+00:00",
  "updated_at": "2026-01-20T14:30:00+00:00"
}
```

**Error responses:**

- `400 Bad Request`: Missing fields (slug, title) or invalid slug format
- `401 Unauthorized`: Missing or invalid authentication token
- `403 Forbidden`: User does not have author role

**Example curl:**

```bash
TOKEN="your_jwt_token_here"

curl -X POST http://localhost:5000/api/posts \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "slug": "my-first-post",
    "title": "My First Blog Post"
  }'
```

**Slug format:**

- Must be lowercase alphanumeric with hyphens only
- Cannot contain spaces, underscores, or special characters
- Example valid slugs: `hello-world`, `my-post-123`, `draft-2026`

#### Get Draft

Retrieve a draft post by slug.

**Endpoint:** `GET /api/posts/:slug`

**Authentication:** Required

**Request parameters:**

- `slug` (path): The post slug identifier

**Response (200 OK):**

```json
{
  "id": 1,
  "slug": "my-first-post",
  "title": "My First Blog Post",
  "author_id": 42,
  "html_content": null,
  "published": false,
  "published_at": null,
  "created_at": "2026-01-20T14:30:00+00:00",
  "updated_at": "2026-01-20T14:30:00+00:00"
}
```

**Error responses:**

- `401 Unauthorized`: Missing or invalid authentication
- `403 Forbidden`: User cannot access another author's draft (non-admin)
- `404 Not Found`: Draft does not exist

**Access control:**

- Authors can only view their own drafts
- Admins can view any draft

**Example curl:**

```bash
TOKEN="your_jwt_token_here"

curl http://localhost:5000/api/posts/my-first-post \
  -H "Authorization: Bearer $TOKEN"
```

#### Save Draft

Update draft content.

**Endpoint:** `PUT /api/posts/:slug`

**Authentication:** Required

**Request body:**

```json
{
  "content": "# My Post\n\nThis is the markdown content of my post."
}
```

**Response (200 OK):**

```json
{
  "message": "Draft saved successfully",
  "slug": "my-first-post"
}
```

**Error responses:**

- `400 Bad Request`: Missing content field
- `401 Unauthorized`: Missing or invalid authentication
- `403 Forbidden`: User cannot edit another author's draft (non-admin)
- `404 Not Found`: Draft does not exist

**Notes:**

- Saves raw markdown content only (rendering happens on publish)
- Automatically commits to GitHub for version history
- Updates the `updated_at` timestamp

**Example curl:**

```bash
TOKEN="your_jwt_token_here"

curl -X PUT http://localhost:5000/api/posts/my-first-post \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "content": "# My First Blog Post\n\nWelcome to my blog!"
  }'
```

#### Publish Post

Publish a draft, rendering markdown to HTML and making it visible.

**Endpoint:** `POST /api/posts/:slug/publish`

**Authentication:** Required

**Response (200 OK):**

```json
{
  "id": 1,
  "slug": "my-first-post",
  "title": "My First Blog Post",
  "author_id": 42,
  "html_content": "<h1>My First Blog Post</h1>\n<p>Welcome to my blog!</p>\n",
  "published": true,
  "published_at": "2026-01-20T14:35:00+00:00",
  "created_at": "2026-01-20T14:30:00+00:00",
  "updated_at": "2026-01-20T14:35:00+00:00"
}
```

**Error responses:**

- `400 Bad Request`: Post already published
- `401 Unauthorized`: Missing or invalid authentication
- `403 Forbidden`: User cannot publish another author's post (non-admin)
- `404 Not Found`: Draft does not exist

**Pipeline on publish:**

1. Reads draft markdown from filesystem
1. Renders markdown to HTML using markdown-it-py
1. Applies syntax highlighting to code blocks with Pygments
1. Sanitizes HTML with Bleach (allowlist-based)
1. Stores rendered HTML in database
1. Updates publication status and timestamps
1. Commits changes to GitHub

**Example curl:**

```bash
TOKEN="your_jwt_token_here"

curl -X POST http://localhost:5000/api/posts/my-first-post/publish \
  -H "Authorization: Bearer $TOKEN"
```

#### Unpublish Post

Hide a published post from public view.

**Endpoint:** `POST /api/posts/:slug/unpublish`

**Authentication:** Required

**Response (200 OK):**

```json
{
  "id": 1,
  "slug": "my-first-post",
  "title": "My First Blog Post",
  "author_id": 42,
  "html_content": "<h1>My First Blog Post</h1>\n<p>Welcome to my blog!</p>\n",
  "published": false,
  "published_at": "2026-01-20T14:35:00+00:00",
  "created_at": "2026-01-20T14:30:00+00:00",
  "updated_at": "2026-01-20T14:40:00+00:00"
}
```

**Error responses:**

- `400 Bad Request`: Post is not published
- `401 Unauthorized`: Missing or invalid authentication
- `403 Forbidden`: User cannot unpublish another author's post (non-admin)
- `404 Not Found`: Post does not exist

**Notes:**

- Removes post from public view but keeps HTML content in database
- HTML content remains accessible via API to authenticated users
- Published timestamp is preserved

**Example curl:**

```bash
TOKEN="your_jwt_token_here"

curl -X POST http://localhost:5000/api/posts/my-first-post/unpublish \
  -H "Authorization: Bearer $TOKEN"
```

#### Delete Draft

Delete a draft post permanently.

**Endpoint:** `DELETE /api/posts/:slug`

**Authentication:** Required

**Response:**

204 No Content

**Error responses:**

- `400 Bad Request`: Post is published (must unpublish first)
- `401 Unauthorized`: Missing or invalid authentication
- `403 Forbidden`: User cannot delete another author's draft (non-admin)
- `404 Not Found`: Draft does not exist

**Notes:**

- Cannot delete published posts (unpublish first)
- Removes draft from filesystem, database, and GitHub
- This operation is permanent

**Example curl:**

```bash
TOKEN="your_jwt_token_here"

curl -X DELETE http://localhost:5000/api/posts/my-first-post \
  -H "Authorization: Bearer $TOKEN"
```

#### List Author's Posts

List all posts belonging to the authenticated user.

**Endpoint:** `GET /api/my-posts`

**Authentication:** Required

**Query parameters:**

- `filter` (optional): Filter posts by status: `all` (default), `drafts`, `published`
- `page` (optional): Page number (1-indexed, default: 1)
- `limit` (optional): Posts per page, 1-100 (default: 20)

**Response (200 OK):**

```json
{
  "posts": [
    {
      "id": 1,
      "slug": "my-first-post",
      "title": "My First Blog Post",
      "author_id": 42,
      "html_content": "<h1>My First Blog Post</h1>\n<p>Welcome to my blog!</p>\n",
      "published": true,
      "published_at": "2026-01-20T14:35:00+00:00",
      "created_at": "2026-01-20T14:30:00+00:00",
      "updated_at": "2026-01-20T14:35:00+00:00"
    }
  ],
  "total_count": 15,
  "total_pages": 1,
  "page": 1,
  "limit": 20
}
```

**Error responses:**

- `400 Bad Request`: Invalid query parameters (invalid filter or pagination)
- `401 Unauthorized`: Missing or invalid authentication

**Examples:**

```bash
TOKEN="your_jwt_token_here"

curl "http://localhost:5000/api/my-posts" \
  -H "Authorization: Bearer $TOKEN"

curl "http://localhost:5000/api/my-posts?filter=drafts&page=1&limit=10" \
  -H "Authorization: Bearer $TOKEN"

curl "http://localhost:5000/api/my-posts?filter=published" \
  -H "Authorization: Bearer $TOKEN"
```

### Markdown Rendering Pipeline

The post management system uses a multi-step pipeline to safely convert markdown to HTML with syntax highlighting.

#### Overview

```text
Markdown Draft
    ↓
1. Parse with markdown-it-py
    ↓
2. Highlight code blocks with Pygments
    ↓
3. Sanitize HTML with Bleach
    ↓
Published HTML
```

#### Step 1: Markdown Parsing

The system uses **markdown-it-py**, a Python implementation of the markdown-it JavaScript library.

**Features:**

- CommonMark-compliant markdown parsing
- Support for tables, strikethrough, code blocks, etc.
- Link and image support
- Nested lists and blockquotes

**Supported markdown:**

```markdown
# Headings

## Level 2
### Level 3

**Bold text** and *italic text*

- Unordered lists
  - Nested items
  - More items

1. Ordered lists
2. Second item

[Links](https://example.com)

![Images](https://example.com/image.png)

> Block quotes
> can span multiple lines

`inline code` and code blocks:

    python
    def hello():
        print("world")
```

#### Step 2: Syntax Highlighting

Code blocks are highlighted using **Pygments**, a syntax highlighter supporting 500+ languages.

**Features:**

- Automatic language detection if not specified
- Fallback to plain text for unknown languages
- HTML-escaped code to prevent injection
- CSS classes for styling

**Code block syntax:**

````markdown
```python
def factorial(n):
    return 1 if n <= 1 else n * factorial(n - 1)
```

```javascript
const sum = (a, b) => a + b;
```

```
Plain text code block (language not specified)
```
````

**Rendered output:**

The highlighted code is wrapped in `<pre>` tags with CSS classes for styling:

```html
<div class="highlight highlight-python">
  <pre>
    <span class="k">def</span> <span class="nf">factorial</span>(<span class="n">n</span>):
      <span class="k">return</span> <span class="mi">1</span> <span class="k">if</span> <span class="n">n</span> <span class="o">&lt;=</span> <span class="mi">1</span> <span class="k">else</span> <span class="n">n</span> <span class="o">*</span> <span class="n">factorial</span>(<span class="n">n</span> <span class="o">-</span> <span class="mi">1</span>)
  </pre>
</div>
```

**Supported languages:**

Common languages include: Python, JavaScript, TypeScript, Java, C++, C#, Go, Rust, Ruby, PHP, SQL, Bash, HTML, CSS, JSON, YAML, and 400+ more.

#### Step 3: HTML Sanitization

The rendered HTML is sanitized using **Bleach**, an allowlist-based HTML sanitizer that removes dangerous content while preserving safe formatting.

**Allowed tags:**

- **Headings:** `<h1>`, `<h2>`, `<h3>`, `<h4>`, `<h5>`, `<h6>`
- **Text formatting:** `<p>`, `<strong>`, `<em>`
- **Lists:** `<ul>`, `<ol>`, `<li>`
- **Code:** `<code>`, `<pre>`, `<div>` (for syntax highlighting)
- **Links and images:** `<a>`, `<img>`
- **Tables:** `<table>`, `<thead>`, `<tbody>`, `<tr>`, `<th>`, `<td>`
- **Other:** `<blockquote>`, `<br>`, `<hr>`, `<span>`

**Allowed attributes:**

- **Links (`<a>`):** `href`, `title`, `rel`
- **Images (`<img>`):** `src`, `alt`, `title`

**Security measures:**

1. **Dangerous tags removed:** `<script>`, `<style>`, `<iframe>`, `<object>` and their contents are completely removed
1. **Protocol filtering:** Only `http://`, `https://`, and `mailto:` protocols allowed
1. **External link security:** All external links (`http://`, `https://`) automatically get `rel="nofollow noreferrer"` attributes
1. **XSS prevention:** Event handlers and inline styles removed

**Examples of filtered content:**

| Input                               | Output                                                     | Reason                          |
| ----------------------------------- | ---------------------------------------------------------- | ------------------------------- |
| `<script>alert('xss')</script>`     | *(removed)*                                                | Script tags completely stripped |
| `<a href="javascript:alert()">`     | `<a>` (no href)                                            | JavaScript protocol removed     |
| `<a href="https://example.com">`    | `<a href="https://example.com" rel="nofollow noreferrer">` | External link protection added  |
| `<img src="x" onerror="alert()">`   | `<img src="x">`                                            | Event handler removed           |
| `<style>body{display:none}</style>` | *(removed)*                                                | Style tags completely stripped  |

### Draft File Format

Draft posts are stored as markdown files with YAML front matter in the `drafts/` directory.

#### Directory Structure

```text
drafts/
├── my-first-post.md
├── hello-world.md
├── draft-2026-01-20.md
└── .git/                # Separate git repository for version control
```

Each draft file corresponds to one post slug.

#### File Format

Files are stored as markdown with YAML front matter separated by `---` delimiters.

**Example draft file (`drafts/my-first-post.md`):**

```markdown
---
title: My First Blog Post
author: user_abc123
created_at: '2026-01-20T14:30:00+00:00'
published: false
tags:
- blogging
- first-post
---

# My First Blog Post

Welcome to my blog! This is my first post.

## Subsection

Here's some content with **bold** and *italic* text.

```

#### YAML Front Matter Fields

All fields are required unless noted otherwise.

| Field          | Type              | Required | Description                                                 | Example                       |
| -------------- | ----------------- | -------- | ----------------------------------------------------------- | ----------------------------- |
| `title`        | string            | Yes      | Post title displayed to readers                             | `"My First Blog Post"`        |
| `author`       | string            | Yes      | Clerk user ID of the post author                            | `"user_abc123"`               |
| `created_at`   | ISO 8601 datetime | Yes      | UTC timestamp when draft was created                        | `"2026-01-20T14:30:00+00:00"` |
| `published`    | boolean           | Yes      | Whether the post is published                               | `false`                       |
| `published_at` | ISO 8601 datetime | Optional | UTC timestamp when first published (omitted if unpublished) | `"2026-01-20T14:35:00+00:00"` |
| `tags`         | string array      | No       | List of tags for categorization                             | `["blogging", "tutorial"]`    |

#### Front Matter Examples

**Draft post (unpublished):**

```yaml
---
title: Work in Progress
author: user_xyz789
created_at: '2026-01-20T10:00:00+00:00'
published: false
tags: []
---
```

**Published post:**

```yaml
---
title: Published Guide
author: user_xyz789
created_at: '2026-01-15T08:30:00+00:00'
published: true
published_at: '2026-01-20T14:35:00+00:00'
tags:
- tutorial
- guides
---
```

#### Markdown Content

Everything after the closing `---` delimiter is the raw markdown content.

**Features:**

- Supports all CommonMark markdown syntax
- Code blocks with language-specific syntax highlighting
- Tables, lists, blockquotes, links, and images
- Rendered HTML is generated only when post is published

**Storage:**

- Stored in plain text (easy to version control and edit)
- Stored on filesystem at `drafts/{slug}.md`
- Backed up to GitHub API automatically on every save
- Supports concurrent editing with proper file locking

#### Workflow

1. **Draft created:** When you create a draft via the API, a new `.md` file is created with initial YAML front matter and blank content
1. **Draft saved:** Each `PUT /api/posts/:slug` saves the markdown content to the filesystem and commits to GitHub
1. **Draft published:** When you publish, the markdown is rendered to HTML, sanitized, and stored in the database; `published: true` is set in front matter
1. **Draft unpublished:** Setting `published: false` hides the post but keeps the rendered HTML stored

## Testing

### Backend Testing

```bash
cd backend

# Run all tests
uv run pytest

# Run tests by type
uv run pytest tests/unit
uv run pytest tests/integration

# Generate a coverage report
uv run pytest --cov=src/backend
```

### Frontend Testing

```bash
cd frontend

# Run unit tests
npm test

# Run end-to-end tests
npm run test:e2e
```

### Pre-commit Hooks

The project uses pre-commit hooks to enforce code quality before commits. Hooks automatically run on `git commit` and will block commits if checks fail.

**Installed hooks:**

- **Python**: Ruff linting/formatting, mypy type checking
- **JavaScript/TypeScript**: Biome linting/formatting
- **General**: Trailing whitespace removal, YAML validation, merge conflict detection

**Setup:**

```bash
# Install pre-commit (one-time setup)
uv tool install pre-commit
uvx pre-commit install

# Manual run (tests all files)
uvx pre-commit run --all-files
```

#### Common hook failures

| Error                 | Fix                                    |
| --------------------- | -------------------------------------- |
| `Ruff format failed`  | Run `uvx ruff format .` in backend/    |
| `Biome check failed`  | Run `biome check --write` in frontend/ |
| `mypy type errors`    | Fix type annotations in flagged files  |
| `Trailing whitespace` | Auto-fixed by hook, re-stage files     |

## Deployment

Deployment to the cPanel hosting environment is automated with a bash script.

### Automated Deployment to cPanel

The `scripts/deploy.sh` script handles all aspects of the deployment, including:

- Provisioning the database and user.
- Uploading backend and frontend code.
- Installing dependencies on the server.
- Registering the application with the Passenger WSGI server.
- Verifying the deployment with health checks.

**For full instructions, refer to the official deployment guide:**
➡️ **[cPanel Deployment Guide](docs/DEPLOYMENT.md)**

---

## Troubleshooting

| Problem                       | Cause                 | Solution                                                             |
| :---------------------------- | :-------------------- | :------------------------------------------------------------------- |
| `ModuleNotFoundError`         | Not using `uv run`    | Always prefix Python commands with `uv run` (e.g., `uv run pytest`). |
| PostgreSQL connection refused | Database not running  | Start your local PostgreSQL service.                                 |
| API calls fail with 404       | Backend not running   | Start the Flask server: `cd backend && uv run dev_flask`.            |
| `CORS error` in browser       | CORS misconfiguration | Ensure `CORS(app)` is configured in `backend/src/backend/main.py`.   |

## CI/CD

### GitHub Actions Workflows

Two workflows run automatically on push and pull requests to `main`:

#### Backend CI (`backend-ci.yml`)

- **Python version:** 3.13
- **Steps:**
  1. Install uv and sync dependencies
  1. Run Ruff linting and formatting checks
  1. Run mypy type checking
  1. Run pytest with coverage (must be 80%+)
  1. Upload coverage report to Codecov
  1. Build backend artifacts

#### Frontend CI (`frontend-ci.yml`)

- **Node versions:** 22.18, 24.6 (matrix)
- **Steps:**
  1. Install npm dependencies
  1. Run Biome linting and formatting checks
  1. Run Vitest tests with coverage (must be 70%+)
  1. Run Playwright e2e tests
  1. Upload test artifacts and coverage
  1. Build production bundle

**Branch protection:**

Both CI workflows must pass before merging to `main`.

### Pre-deployment Checklist

Before deploying to production:

- [ ] All CI checks pass (green checkmarks on GitHub)
- [ ] Coverage targets met (80% backend, 70% frontend)
- [ ] Manual smoke test on staging environment
- [ ] Database migrations tested
- [ ] Environment variables configured on production
- [ ] Backup current production database
- [ ] Monitor logs for 1 hour post-deployment

## Contributing

### Development Workflow

1. **Create feature branch**

   ```bash
   git checkout -b feature/your-feature-name
   ```

1. **Write failing tests (TDD)**

   ```bash
   # Backend
   cd backend && uv run pytest tests/unit/test_new_feature.py

   # Frontend
   cd frontend && npm test -- tests/NewComponent.test.jsx
   ```

1. **Implement feature**

   - Follow existing patterns in codebase
   - Keep domain logic in `domain/` layer
   - Infrastructure concerns in `infrastructure/`

1. **Ensure tests pass**

   ```bash
   uv run pytest          # Backend
   npm test               # Frontend
   ```

1. **Run quality checks**

```bash
uvx ruff check --fix . # Backend lint
biome check --write # Frontend lint/format
uv run mypy src/ # Type checking
```

6. **Commit with conventional commits format**

```bash
git add .
git commit -m "feat: add post revision comparison API"
```

7.**Push and create PR**

```bash
git push origin feature/your-feature-name
#Create PR on GitHub
```

### Commit Message Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```text
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code restructuring (no behavior change)
- `test`: Add or modify tests
- `chore`: Build process or auxiliary tool changes

**Examples:**

```text
feat(comments): add reply functionality with @mentions
fix(auth): resolve Clerk session timeout issue
docs(readme): update deployment instructions
test(posts): add integration tests for publish workflow
```

### Code Review Guidelines

PRs must meet these criteria before merging:

- [ ] All CI checks pass (backend-ci and frontend-ci)
- [ ] Coverage targets met (no decrease in coverage)
- [ ] Pre-commit hooks pass
- [ ] At least one approving review
- [ ] No merge conflicts with `main`
- [ ] Conventional commit message format
- [ ] Tests added for new functionality
- [ ] Documentation updated if API changes

## Resources & Links

### Documentation

- [Deployment Guide](docs/deployment.md) - Production deployment instructions
- [API Reference](docs/api.md) - REST API endpoints documentation

### External Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [React Documentation](https://react.dev/)
- [uv Documentation](https://docs.astral.sh/uv/)
- [Clerk Authentication](https://clerk.com/docs)
- [Resend Email API](https://resend.com/docs)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [Domain-Driven Design](https://martinfowler.com/bliki/DomainDrivenDesign.html)
- [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)

### Development Tools

- [Ruff](https://docs.astral.sh/ruff/) - Python linter and formatter
- [Biome](https://biomejs.dev/) - JavaScript/TypeScript linter and formatter
- [pytest](https://docs.pytest.org/) - Python testing framework
- [Vitest](https://vitest.dev/) - Vite-native test framework
- [Playwright](https://playwright.dev/) - End-to-end testing

### Support

- **Issues:** [GitHub Issues](https://github.com/ashrobertsdragon/markdown-blog/issues)
- **Email:** See [pyproject.toml](backend/pyproject.toml)

---

**License:** MIT

**Last Updated:** 2025-12-22
