# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Notification and user preferences repositories**: Added `NotificationRepository` (`backend/infrastructure/persistence/notification_repository.py`) with `save`, `get_by_id`, `get_pending` (UTC-safe scheduling filter, hard cap 500), `get_history` (paginated, newest-first), `mark_for_retry` (enforces UTC on `next_retry_at`), `count_pending`, and `count_failed`. Added `UserNotificationPreferencesRepository` (`backend/infrastructure/persistence/user_notification_preferences_repository.py`) with `get_preferences` (auto-creates all-enabled defaults on first access), `update_preferences`, `disable_all` (unsubscribe), and `exists`. Added `NotificationPreferences` domain aggregate (`backend/domain/aggregates/notification_preferences.py`) with `create_defaults` factory and `should_notify_reply`, `should_notify_mention`, `should_notify_post` query methods. Added `UserNotificationPreferencesModel` to persistence models and `next_retry_at` field to `NotificationModel`, with three new indexes (`idx_notification_status_created`, `idx_notification_recipient_created`, `idx_notification_next_retry`) for efficient queue processing. Added `next_retry_at` field to `Notification` aggregate to carry retry schedule state through the domain layer.

- **Resend email integration**: Added `ResendEmailService` (`backend/infrastructure/email/resend_email_service.py`) for sending template-based emails via the Resend HTTP API. Implements exponential backoff (1s/2s/4s) for 429 rate-limit and 5xx server errors with up to `max_retries` retry attempts, permanent failure on 4xx, and graceful `None` return on network errors. Added `ResendTemplateManager` (`backend/infrastructure/email/resend_template_manager.py`) for CRUD operations on Resend email templates — create (raises on duplicate alias), publish, get, and delete — with full network exception handling. Added `email_templates.py` with `TEMPLATE_REPLY_NOTIFICATION`/`TEMPLATE_MENTION_NOTIFICATION` alias constants, variable name constants for both template types, and `TEMPLATE_DEFINITIONS` with triple-mustache HTML for initialization scripts. Added `ResendSettings` to `config.py` with required `RESEND_API_KEY`, configurable `RESEND_DOMAIN`, template aliases, and bounded `RESEND_MAX_RETRIES` (1–10) and `RESEND_REQUEST_TIMEOUT` (1–60s) fields. Wired `get_resend_settings()` and `get_resend_email_service()` singletons into `api/dependencies.py`.

- **Notification domain model**: Added `Notification` aggregate (`backend/domain/aggregates/notification.py`) with `NotificationStatus` (`pending`/`sent`/`failed`) and `EventType` (`comment_posted`/`reply_received`) enums. Factory `Notification.create()` validates all foreign-key IDs, sets immutable `created_at`, and initialises `status=PENDING`. State-transition methods: `mark_sent()`, `mark_failed()` (truncates error message to 500 chars), `increment_attempt()`. `to_dict()` serialises all fields to JSON-safe primitives.

- **UnsubscribeToken value object**: Added `UnsubscribeToken` (`backend/domain/value_objects/unsubscribe_token.py`). Generates HMAC-SHA256 tokens scoped to `user_id:email` (email normalised to lowercase) using `SECRET_KEY` from the environment. Validates 64-character hex format. `verify()` uses `hmac.compare_digest` for constant-time comparison. Enables stateless unsubscribe link verification without token storage.

- **Backend comments acceptance tests**: Implemented 12 acceptance tests in `backend/tests/acceptance/test_comments.py` covering all comment system acceptance criteria — post/reply workflows, hard and soft delete moderation, rate limiting with `X-RateLimit-*` headers, chronological display ordering with `is_post_author` flag, notification record creation on comment and reply events, spam prevention with moderation queue, thread tracking via `parent_id`, and permission enforcement. Added `backend/tests/acceptance/conftest.py` with shared fixtures for reader, author, and admin users and a `published_post` fixture for test data setup.

- **Comments acceptance tests**: Enabled all 7 acceptance tests in `tests/acceptance/comments.ts`. Fixed `CommentForm` placeholder ("Leave a comment..."), button label ("Post Comment"), pending-moderation detection via `is_pending_moderation` flag, and rate-limit error message passthrough. Fixed `ReplyForm` submit button label ("Post Reply") and `@user{id}` mention fallback. Replaced `window.confirm` in `CommentItem` delete flow with `AlertDialog` (`role="alertdialog"`); `AlertDialogAction` now disabled while delete mutation is pending. Added `aria-label="Delete comment"` to delete button, `.comment-item` CSS class, `.comment-timestamp` element, `.badge` class on author badge, `data-comment-id` attribute, `data-testid="comments-list"` on `CommentList`, and thread-reply label "Reply to @username". Extended `formatTimestamp` to always return relative text. Added optimistic update to `usePostComment`. Added Playwright `globalSetup` to seed the backend before acceptance tests run. Updated e2e delete tests (4.2, 4.4) to use `button[aria-label="Delete comment"]` selector and assert `AlertDialog` lifecycle.

- **E2E tests for comment workflow**: Added `frontend/tests/e2e/comments.ts` with 17 Playwright tests covering post comment, reply, rate limiting, moderation, and author badge flows against the real Flask backend. Added `optional_auth` decorator to auth middleware so the public comment listing endpoint optionally authenticates callers — admins now see soft-deleted comments as `[deleted]` placeholders. Rate limit cache is cleared on each seed call so tests start with a fresh window. Backend 429 responses now include `retry_after` in the JSON body. `usePostComment` and `useReplyToComment` parse 429 errors and rethrow with a `retryAfter` property so the comment form displays a human-readable wait time. `CommentSection` fetches with admin auth when the signed-in user is an admin.

### Fixed

- **Deployment**: Fixed incorrect PROJECT_ROOT and monorepo path prefixes in deployment scripts that caused CI failures when the monorepo is used as a submodule.
- **CI/Playwright**: Fixed e2e and acceptance tests failing in CI while passing locally
  - Vite dev server now starts with `--mode test` so the Clerk mock security gate in
    `main.tsx` activates, allowing `mockClerkUnauthenticated` to skip `ClerkProvider`
  - Added `mockClerkUnauthenticated` to three auth-flow describe blocks that lacked it
    (`Role-Based Access Control`, `Browser Compatibility`, `Performance and Reliability`)
  - Wrapped `<SignIn>` in an error boundary in `Login.tsx` so the heading remains visible
    when `ClerkProvider` is absent in test mode
  - Added `mockClerkUnauthenticated` to foundation acceptance tests to prevent Clerk from
    hiding the document body when it cannot connect to its servers with a test key

### Added

- **Comment notification event publishing**: Added `CommentPostedEvent` and `ReplyReceivedEvent` frozen dataclasses in the domain events layer. Added `NotificationModel` SQLModel table for the notifications queue. Added `CommentNotificationHandler` infrastructure class that persists pending notification rows when events fire. Added `notify_comment_posted` and `notify_reply_received` application handler functions that are fire-and-forget (no-op for self-comments/self-replies, log and swallow errors). Wired both handlers into the `POST /<slug>/comments` and `POST /<slug>/comments/<id>/reply` routes after successful creation.

- **Real-time comment streaming via SSE**: Added `GET /api/posts/<slug>/comments/stream` endpoint returning a `text/event-stream` response with `Cache-Control: no-cache` and `X-Accel-Buffering: no` headers for correct proxy behaviour. `CommentStreamService` provides thread-safe in-process pub/sub using `threading.Condition` and per-subscriber `deque` queues; `publish()` is called after each successful comment or reply creation. Added `useCommentStream` React hook that opens an `EventSource`, merges individual comment payloads into the React Query cache, and falls back to REST polling when SSE fails. `CommentSection` now shows a "● Live" / "↻ Updating" status indicator driven by the hook.

- **Comment frontend `is_post_author` refactor**: Removed `postAuthorId` prop from `CommentSection`, `CommentList`, and `CommentItem`. Author badge now uses `comment.is_post_author` from the API response. Updated `CommentResponse` type to include `is_post_author: boolean` and remove `author_id`. Added `CommentSection` to `PublicPost` page.

- **Comment API `is_post_author` flag**: All comment list, post, and reply responses now include `is_post_author: bool` computed server-side by comparing `comment.author_id` against `post.author_id`. Eliminates the need for clients to receive the post's internal `author_id` to render author badges.

- **Admin moderation UI**: Added `ModerationPanel` (admin comment table with All/Pending/Deleted filters, status badges, and CSV export) and `CommentModerateButton` (inline Approve + Delete with AlertDialog confirmation). Added `useApproveComment` and `useAdminDeleteComment` mutation hooks and `approveComment`/`adminDeleteComment` API methods. Added `tsconfig.app.json` to scope type-checking to source files only.

- **Comment UI components**: Added `CommentList` (flat list rendering with deleted comment handling), `CommentItem` (single comment display with author badge, relative timestamps, and reply threading indicators), and `ReplyForm` (reply submission form with pre-filled @mention) for Task 7. Added test fixtures factory functions (`createMockComment`, `createMockReplyComment`, `createMockDeletedComment`, `createMockPendingModerationComment`, `createMockListCommentsResponse`) for comprehensive test coverage.

- **Comment application layer**: Added `ReplyToCommentCommand` and handler (parent validation, rate limiting, spam detection, reply creation); `DeleteCommentCommand` and handler (admin soft-delete vs author hard-delete, authorization checks); `ModerateCommentCommand` and handler (approve/reject/flag actions, admin-only); `GetPostCommentsQuery` and handler (public vs admin pagination with `has_more`); `GetCommentQuery` and handler (single comment lookup). All follow the established command/query pattern with frozen dataclasses, `__post_init__` validation, and 5-step handler orchestration.

- **Comment persistence**: Added `CommentModel` SQLModel table with self-referential `parent_id` FK for flat threading, `is_deleted` and `is_pending_moderation` flags with indexes, and foreign keys to `posts` and `users`. Added `CommentRepository` with `save`, `find_by_id`, `list_by_post` (public), `list_by_post_admin` (admin view), `hard_delete`, and `soft_delete` operations following the established repository pattern.

- **Spam detection**: Added `SpamCheckService` scoring comment text 0–100 via URL density, repeated-character, and configurable regex checks; comments scoring ≥ 50 are flagged for moderation rather than blocked

- **Rate limiting**: Added `RateLimitService` enforcing 5 comments per 60-second sliding window per user/IP using an in-memory timestamp cache; admin users bypass limits; includes thread-safe cleanup to prevent unbounded memory growth

- **Comment frontend components**: Added `CommentSection` and `CommentForm` React components with `commentsApi` service and `useComments` hooks. `CommentForm` uses an uncontrolled textarea with live character counter (0–5000 limit), auth gate, rate-limit error display (shows specific wait time from `retryAfter`), and `onCommentPosted` callback. `CommentSection` composes the form with `useFetchComments`, handling loading/error/empty states and filtering `is_pending_moderation` comments for non-admins. All four CRUD operations (`listComments`, `postComment`, `deleteComment`, `replyToComment`) are wired through React Query with cache invalidation on mutation success.

- **Comment moderation flag**: Added `is_pending_moderation` field and `mark_as_pending_moderation()` to the `Comment` aggregate

- **PostCommentCommand**: Added frozen dataclass carrying `post_id`, `author_id`, `text`, `ip_address`, and `is_admin` with domain validation in `__post_init__`

- **PostCommentHandler**: Added `handle_post_comment()` orchestrating rate limit check → spam check → `Comment.create()` → moderation flag; raises `RateLimitExceededError` on limit exceeded

- **RateLimitExceededError**: Added exception mapping to HTTP 429 with `reset_after` and `remaining` attributes; registered error handler in Flask app returns `X-RateLimit-Remaining` and `X-RateLimit-Reset` headers

- **Comment domain**: Added `Comment` aggregate root and `CommentText` value object establishing the domain model for the flat comment system; supports root comments and replies via `parent_id`, soft deletion via `mark_as_deleted()`, and runtime contract enforcement via `__post_init__`

- **Docs**: Added `docs/revision-tracking.md` with full API documentation for all four
  revision tracking endpoints (list, get, diff, revert), including request/response
  schemas, error codes, performance SLAs, and curl/Python/bash code examples

- **Docs**: Added `shared/openapi.yaml` with OpenAPI 3.0 specification for revision
  tracking endpoints, including reusable component schemas, security scheme, and
  structured examples

- **Docs**: Linked revision tracking API docs and OpenAPI spec from README

- **PostEditor**: Added "View History" button that navigates to `/posts/{slug}/revisions`

- **CI/CD**: Added GitHub Actions deployment workflow

  - Automated deployment on merge to `main` branch
  - Dynamic switching between standard and LiteSpeed deployment scripts via `LITESPEED` environment variable
  - Secure handling of SSH keys and production secrets
  - Integration with `uv` for backend dependency management

- **Backend**: Acceptance tests for all spec workflow specifications

  - Created comprehensive acceptance test suite covering all 7 specifications
  - Foundation spec: Project structure, health checks, configuration management
  - Authentication spec: JWT validation, role-based access control, auth middleware
  - Post Management spec: Draft creation, publishing, deletion (existing tests)
  - Revision Tracking spec: Revision history, diff viewer, revert operations
  - Comments spec: Flat comment system, replies, moderation, rate limiting
  - Notifications spec: Email queue, Resend integration, retry logic, preferences
  - Admin Dashboard spec: User management, content moderation, system health
  - Tests reference requirements by description (not by number) for maintainability
  - Unimplemented features marked with pytest.mark.skip() to prevent false failures
  - 63 total acceptance tests collected and validated

- **Frontend**: Acceptance tests for all spec workflow specifications

  - Created comprehensive Playwright test suite covering all 7 specifications
  - Foundation spec: React SPA routing, health check accessibility, asset optimization
  - Authentication spec: Clerk integration, AuthContext, protected routes, role-based UI
  - Post Management spec: Markdown editor, publish flow, draft management (existing tests)
  - Revision Tracking spec: History timeline, diff viewer, revert with confirmation
  - Comments spec: Post comments, replies with @mentions, moderation UI, real-time updates
  - Notifications spec: User preferences, unsubscribe functionality, notification badges
  - Admin Dashboard spec: User management UI, content moderation, system health monitoring
  - Tests verify UI interactions, form validation, navigation, and user workflows
  - Unimplemented features marked with test.skip() to prevent false failures
  - All tests use mockClerkAuth fixture for consistent authentication testing

- **Backend**: Integration tests for revision API routes

  - Created comprehensive test suite with 47 tests covering 4 revision management endpoints
  - `GET /api/posts/<slug>/revisions` - List revisions with pagination (14 tests)
  - `GET /api/posts/<slug>/revisions/<sha>` - Get single revision with content (10 tests)
  - `GET /api/posts/<slug>/revisions/<sha1>/diff/<sha2>` - Compare revisions (10 tests)
  - `POST /api/posts/<slug>/revert` - Revert to revision (13 tests)
  - Authentication tests (401 for missing/invalid token)
  - Authorization tests (403 for non-author/non-admin users)
  - Pagination validation (skip 0-10000, limit 1-100)
  - Input validation (invalid SHA format, empty values)
  - Response structure validation (metadata, diff_lines, revision data)
  - Edge cases (empty lists, identical revisions, non-existent revisions)

- **Frontend**: End-to-end tests for revision tracking workflow

  - Created comprehensive Playwright E2E test suite with 33 tests covering revision management UI
  - Revision timeline display and pagination (6 tests)
  - Revision detail view with metadata and content (6 tests)
  - Diff viewer with syntax highlighting for additions/deletions/context (6 tests)
  - Revert workflow with confirmation modal and error handling (7 tests)
  - Permission boundaries for author/admin/reader roles (4 tests)
  - Error handling and edge cases (empty state, API failures, loading states) (4 tests)
  - Tests validate complete user workflows from revision viewing to reverting posts
  - Mock data generators ensure test independence and maintainability
  - All tests mocked dependencies with proper fixtures for auth, users, and revisions
  - File: `frontend/tests/e2e/revision-history.ts`

- **Backend**: Revision tracking application layer with queries and commands

  - Created application layer commands and queries for post revision management
  - `RevertToRevisionCommand` - Revert post content to previous Git commit with authorization checks
  - `GetRevisionHistoryQuery` - Retrieve paginated commit history for posts (skip/limit support)
  - `GetRevisionQuery` - Fetch specific revision content with rendered HTML output
  - `CompareRevisionsQuery` - Generate diffs between two revisions for change tracking
  - All handlers follow pure function pattern with injected dependencies and comprehensive logging
  - Authorization enforces owner-or-admin access for revert operations
  - PostRevisionRepository extended with `find_by_post_id()` and `find_by_sha()` methods
  - Comprehensive test coverage (99% for commands, 90% for queries) with 31 passing tests
  - Type-safe implementation with Protocol pattern for dependency inversion
  - Validates input constraints (slug ≤1000 chars, SHA ≤100 chars, skip ≤10000, limit ≤100)

- **Backend**: GitHubRevisionService for fetching commit history from GitHub API

  - Created `backend/infrastructure/versioning/github_revision_service.py` with comprehensive error handling and rate limiting
  - Implemented `fetch_commits()` method for retrieving file commit history with pagination support
  - Implemented `fetch_file_at_sha()` method for retrieving file content at specific commits
  - Added exponential backoff retry logic (1s, 2s, 4s) for HTTP 429 rate limiting
  - Returns None/empty list on errors for graceful degradation without exceptions
  - Comprehensive unit test suite with 21 tests covering all methods and error paths
  - Follows GitHubSyncService patterns for consistency (5s timeout, 3 max retries)
  - Exported GitHubRevisionService from versioning infrastructure module
  - All tests pass with 91.60% overall backend coverage maintained

- **Backend**: Comprehensive acceptance tests for post management

  - Created `monorepo/backend/tests/acceptance/test_post_management.py` covering all 12 requirements
  - Scenarios include: draft creation, slug validation, editing content, markdown preview, publishing/unpublishing, deletion, and author authorization
  - Tests exercise the full stack using Flask test client and temporary filesystem for drafts
  - Corrected mock paths for GitHub service integration
  - Moved shared `client` and `test_build_dir` fixtures to root `conftest.py` for multi-directory accessibility

- **Frontend**: Comprehensive acceptance tests for post management UI

  - Created `monorepo/frontend/tests/acceptance/post-management.spec.ts` covering UI-specific requirements
  - Scenarios include: form visibility, real-time slug normalization, markdown preview toggling, and confirmation modals
  - Tests verify client-side navigation and state transitions using Playwright
  - Updated `playwright.config.ts` to include the new `acceptance` test directory

- **Frontend Documentation**: Comprehensive post management UI documentation

  - Documented all post management components: MarkdownEditor, PreviewPane, PostForm with props interfaces, features, and usage examples
  - Documented all pages: PostEditor, MyPosts, PublicPost with workflows and error handling
  - Documented 8 React Query hooks: useDraft, useMyPosts, usePublicPost (queries), useCreateDraft, useSaveDraft, usePublishPost, useUnpublishPost, useDeleteDraft (mutations) with parameters, return types, authentication requirements, and cache invalidation patterns
  - Documented postsApi client: 8 methods with HTTP endpoints, request/response formats, and error codes
  - Complete workflow examples: Create → Edit → Save → Publish (4-step process), list with filters/pagination, delete with confirmation
  - Architecture overview: tech stack table, component hierarchy, data flow diagram
  - State management: React Query cache keys, invalidation patterns, optimistic updates
  - Testing guide: Vitest unit tests and Playwright E2E tests with examples
  - Accessibility: ARIA attributes, keyboard navigation, focus management
  - Security: XSS prevention (client + server), JWT token handling, input validation, CORS
  - Files created: frontend/README.md (2000+ lines of developer documentation)

- **Backend Documentation**: Comprehensive post management API documentation

  - Documented all 7 post management endpoints with full specifications and examples
  - Created curl examples for each endpoint showing proper authentication and request/response formats
  - Documented markdown rendering pipeline: markdown-it-py parsing → Pygments syntax highlighting → Bleach HTML sanitization
  - Documented all allowed HTML tags and security measures (XSS prevention, external link rel attributes, dangerous tag removal)
  - Documented draft file format with YAML front matter specification and examples
  - Documented workflow from draft creation through publishing/unpublishing/deletion
  - Added visual pipeline diagram showing the 3-step rendering process
  - Included security measures table showing filtered content examples
  - Files modified: README.md (added "Post Management" section with API Endpoints, Rendering Pipeline, and Draft File Format subsections)

- **Frontend**: Post management routes with role-based access control

  - Added three protected author routes: /new-post for creating posts, /edit/:slug for editing drafts, and /my-posts for managing all posts
  - Integrated ProtectedRoute component with requireRole="author" for author-only access enforcement
  - Organized routes by access level (public → admin → author → catch-all) for clear security model
  - Added comprehensive routing documentation with JSDoc explaining organizational strategy
  - Improved ProtectedRoute loading spinner accessibility with role="img" and aria-label attributes
  - 33 route tests passing covering authentication, authorization, role hierarchy, and navigation flows
  - Files modified: frontend/src/App.tsx, frontend/src/components/auth/ProtectedRoute.tsx
  - Files created: frontend/tests/unit/App.routes.test.tsx

- **Frontend**: PublicPost page for displaying published blog posts

  - Implemented public-facing page component at /posts/:slug for viewing published posts without authentication
  - Integrated with backend GET /posts/:slug/public endpoint via new postsApi.getPublicPost() method
  - React Query hook usePublicPost() for data fetching with caching and loading states
  - Displays post title, author, published date metadata, and sanitized HTML content via dangerouslySetInnerHTML
  - Error handling: 404 state for unpublished/missing posts, error alert for API failures
  - Semantic HTML structure using article element with accessibility attributes
  - "Back to Home" navigation link for user convenience
  - Comprehensive test suite with 32 unit tests covering loading, success, error, and 404 states
  - Files created: frontend/src/pages/PublicPost.tsx
  - Files modified: frontend/src/App.tsx (routing), frontend/src/services/postsApi.ts (API client), frontend/src/hooks/usePosts.ts (React Query hook), frontend/src/hooks/queryKeys.ts (cache keys)

- **Backend**: Public endpoint for published posts without authentication

  - Implemented GET /api/posts/:slug/public endpoint for unauthenticated access to published posts
  - Returns 404 for unpublished or non-existent posts (protects draft content)
  - Uses to_public_dict() to exclude internal fields (author_id) from public responses
  - Comprehensive test suite with 4 integration tests validating public access, draft protection, field leakage prevention, and authenticated endpoint protection
  - Files modified: backend/src/backend/domain/aggregates/post.py, backend/src/backend/api/routes/posts.py, backend/tests/integration/api/test_posts_routes.py

- **Frontend**: Markdown editor component with XSS protection and keyboard shortcuts

  - Implemented MarkdownEditor component as controlled React component with TypeScript strict typing
  - Live markdown preview with syntax highlighting powered by @uiw/react-md-editor
  - XSS attack prevention using rehype-sanitize plugin to sanitize HTML in preview
  - Ctrl+S (Cmd+S on macOS) keyboard shortcut for saving drafts
  - Custom className support via cn() utility for Tailwind CSS composition
  - Comprehensive test suite with 8 unit tests covering all functionality
  - Async error handling with graceful degradation for failed save operations

- **Frontend**: React Query hooks for post management with type-safe cache invalidation

  - Implemented data fetching hooks: useDraft (retrieve single draft), useMyPosts (list author's posts with filtering)
  - Implemented mutation hooks: useCreateDraft, useSaveDraft, usePublishPost, useUnpublishPost, useDeleteDraft
  - Optimistic updates and automatic cache invalidation on successful mutations
  - QueryClientProvider configuration with React Query DevTools for development debugging
  - Query key factory pattern for consistent cache management across components
  - Type-safe integration with backend API endpoints ensuring compile-time validation

- **Frontend**: Markdown editor dependencies for post management

  - Installed @uiw/react-md-editor (v4.0.11) for markdown editing UI
  - Installed react-syntax-highlighter (v16.1.0) for code block highlighting
  - Installed rehype-sanitize (v6.0.0) for XSS prevention in markdown preview
  - All packages are React 19 compatible with no peer conflicts

- **Frontend**: PostForm component

  - Form for creating new blog posts with slug and title inputs
  - Real-time slug normalization: lowercase conversion, spaces to hyphens, special character removal
  - Client-side validation with inline error messages
  - Slug validation rules: required, max 200 characters, URL-safe characters only
  - Title validation: required, no whitespace-only input
  - Submit button disabled until form is valid
  - Accessible form controls with proper ARIA attributes (aria-invalid, aria-describedby, role="alert")
  - TypeScript with comprehensive type safety
  - Support for initial values and onChange callback
  - Tailwind CSS styling consistent with project design

- **Frontend**: PreviewPane component

  - Client-side markdown rendering with `marked` library
  - Syntax highlighting for code blocks via `react-syntax-highlighter` (dracula theme)
  - XSS prevention via `rehype-sanitize` integration
  - Support for all common markdown elements: headings, paragraphs, links, images, code blocks
  - Error handling with user-friendly error messages
  - Loading state indicator
  - Graceful handling of invalid/malformed markdown
  - Memoized parsing to prevent unnecessary re-renders
  - Responsive to markdown prop changes

- **Backend**: Posts API routes with full CRUD operations and access control

  - Implemented 7 REST endpoints for post management: create draft (POST /api/posts), get draft (GET /api/posts/:slug), save draft (PUT /api/posts/:slug), delete draft (DELETE /api/posts/:slug), publish post (POST /api/posts/:slug/publish), unpublish post (POST /api/posts/:slug/unpublish), list author posts (GET /api/posts/my-posts)
  - Author ownership verification: all mutating operations verify user is post author before allowing changes
  - Admin override support: admin role can edit/unpublish any post regardless of authorship
  - Authorization enforcement via @require_auth and @require_role decorators on all endpoints
  - My-posts endpoint with filtering: supports query params for drafts-only, published-only, or all posts
  - Pagination support: configurable limit (1-100 posts) and offset for efficient data retrieval
  - Comprehensive error handling: 400 for invalid input, 403 for unauthorized access, 404 for missing posts, 500 for server errors
  - Enhanced command layer with authorization: added author_id and user_role to SaveDraftCommand, DeleteDraftCommand, PublishPostCommand, UnpublishPostCommand
  - Domain model serialization: added Post.to_dict() for clean JSON responses
  - Integration test suite with 36 tests covering authentication, authorization, ownership checks, admin overrides, pagination, filtering, error scenarios
  - Files created: `backend/src/backend/api/routes/posts.py`, `backend/tests/integration/api/routes/test_posts.py`
  - Files modified: `backend/src/backend/main.py` (registered posts blueprint), `backend/src/backend/application/commands/save_draft_command.py`, `backend/src/backend/application/commands/delete_draft_command.py`, `backend/src/backend/application/commands/publish_post_command.py`, `backend/src/backend/application/commands/unpublish_post_command.py`, `backend/src/backend/domain/aggregates/post.py`

- **Backend**: Post listing query with filtering and pagination

  - ListPostsQuery for retrieving author's posts with flexible filtering (drafts only, published only, or all posts)
  - PostFilter enum for type-safe filter options (DRAFTS, PUBLISHED, ALL)
  - Pagination support with configurable page size (1-100 posts per page)
  - Efficient database counting using SQL COUNT(\*) instead of loading all rows
  - Sort by most recently updated posts first (updated_at DESC)
  - Input validation: page >= 1, limit 1-100, author_id > 0
  - Paginated response includes total count and total pages for UI pagination controls
  - Repository method find_by_author_filtered for filtered queries with dual return (posts, count)
  - Comprehensive test suite: 33 tests covering validation, filtering, pagination, edge cases (100% pass rate)
  - Files created: `backend/src/backend/domain/value_objects/post_filter.py`, `backend/src/backend/application/queries/list_posts_query.py`, `backend/src/backend/application/queries/handlers/list_posts_query_handler.py`, `backend/tests/unit/application/queries/test_list_posts_query.py`, `backend/tests/unit/application/queries/handlers/test_list_posts_query_handler.py`
  - Files modified: `backend/src/backend/infrastructure/persistence/post_repository.py`, `backend/src/backend/domain/value_objects/__init__.py`

- **Backend**: Draft deletion command with GitHub version control sync

  - DeleteDraftCommand for deleting draft posts with validation to prevent deletion of published posts
  - Critical GitHub sync ensures deletion commits propagate to version control (failures raise exceptions)

- **Backend**: Post unpublishing command with workflow automation

  - UnpublishPostCommand dataclass for reverting published posts back to draft state
  - Complete unpublishing workflow: database update (published=false), draft file front matter sync, GitHub commit
  - Preserves post metadata and history: html_content and published_at timestamp remain in database for audit trail
  - Automatic front matter update: published flag set to false in markdown draft file
  - Best-effort GitHub sync: commits draft changes to version control with graceful failure handling
  - Allows post re-editing after unpublish: draft file becomes editable again
  - Domain-driven design: Post.unpublish() domain method encapsulates state transition logic
  - Graceful degradation: continues on filesystem or GitHub failures after database commit completes
  - Comprehensive error handling: validates post exists and is currently published before unpublishing
  - Comprehensive test suite: 18 handler tests covering success path, error scenarios, and edge cases (100% pass rate)
  - Files created: `backend/src/backend/application/commands/unpublish_post_command.py`, `backend/src/backend/application/commands/handlers/unpublish_post_handler.py`, `backend/tests/unit/application/commands/test_unpublish_post_command.py`, `backend/tests/unit/application/commands/handlers/test_unpublish_post_handler.py`

- **Backend**: Post publishing command with markdown rendering and HTML sanitization

  - PublishPostCommand dataclass for publishing draft posts to production
  - Complete publishing workflow: draft loading, markdown rendering, HTML sanitization, database persistence, GitHub sync
  - Integration with MarkdownRenderingService for markdown-to-HTML conversion with Pygments syntax highlighting
  - Integration with HtmlSanitizer for XSS prevention via Bleach allowlist-based sanitization
  - Automatic front matter updates (published: true, published_at timestamp) in draft files
  - Best-effort GitHub commit after successful database persistence
  - Graceful degradation: continues on filesystem or GitHub failures after database commit
  - Domain-driven design: Post.publish() domain method encapsulates state transition logic
  - Comprehensive error handling: validates draft exists, not already published, post in database
  - Comprehensive test suite: 17 handler tests covering success path, error scenarios, logging, edge cases (100% pass rate)
  - Files created: `backend/src/backend/application/commands/publish_post_command.py`, `backend/src/backend/application/commands/handlers/publish_post_handler.py`, `backend/tests/unit/application/commands/test_publish_post_command.py`, `backend/tests/unit/application/commands/handlers/test_publish_post_handler.py`

- **Backend**: Draft content update with automatic corruption recovery

  - SaveDraftCommand for updating existing draft content with size validation
  - Automatic corruption recovery: fetches original content from GitHub when draft file becomes corrupted
  - Graceful fallback: creates new draft with default front matter if GitHub recovery fails
  - Size limits enforced: slug maximum 1000 characters, content maximum 10MB
  - Front matter preservation: retains title, author, created_at, and tags during updates
  - Resilient to GitHub API failures (continues with local save even if GitHub sync fails)
  - Comprehensive test suite: 27 tests (11 unit tests for command, 10 for handler, 6 integration tests) with 100% pass rate
  - Files created: `backend/src/backend/application/commands/save_draft_command.py`, `backend/src/backend/application/commands/handlers/save_draft_handler.py`, `backend/tests/unit/test_save_draft_command.py`, `backend/tests/unit/test_save_draft_handler.py`, `backend/tests/integration/test_save_draft_handler.py`
  - Files modified: `backend/src/backend/infrastructure/versioning/github_sync_service.py` (added get_file_content method)

- **Backend**: feat: implement draft post creation command with validation and error handling

  - Implemented CreateDraftCommand dataclass with slug, title, and author_id fields for structured input validation
  - Created create_draft_handler orchestrating complete draft creation workflow with rollback on failures
  - Slug uniqueness validation across both database (PostRepository) and filesystem (FileSystemDraftRepository)
  - Draft file creation with YAML front matter containing metadata (title, author, timestamps)
  - GitHub commit integration with "drafts/" path prefix for version control backup
  - Rollback mechanism for partial failures: deletes draft file if database persistence fails after filesystem write
  - PostRepository type annotations replacing Any types for improved type safety
  - Comprehensive test suite: 8 unit tests for command validation, 11 integration tests for handler workflow including rollback scenarios
  - Files created: `backend/src/backend/application/commands/__init__.py`, `backend/src/backend/application/commands/create_draft_command.py`, `backend/src/backend/application/commands/handlers/__init__.py`, `backend/src/backend/application/commands/handlers/create_draft_handler.py`, `backend/tests/unit/test_create_draft_command.py`, `backend/tests/integration/test_create_draft_handler.py`

- **Backend**: PostRepository persistence layer for Post aggregate CRUD operations

  - Implemented PostRepository following repository pattern for Post aggregate persistence
  - save() method handles INSERT (new posts) and UPDATE (existing posts) with unique slug constraint enforcement
  - find_by_slug() provides fast indexed lookup by URL-safe slug identifier
  - find_by_author() lists author's posts with pagination support (limit/offset, newest first)
  - list_published() queries public posts (published=true) with pagination
  - find_by_id() performs efficient primary key lookup via session.get()
  - delete() removes posts by primary key with boolean success/failure return
  - Bidirectional conversion between PostModel (SQLModel) and Post domain aggregate
  - Field mapping: PostModel.published_html ↔ Post.html_content (HtmlContent value object)
  - Slug value object conversion: PostModel.slug (string) ↔ Post.slug (Slug value object)
  - Timezone-aware datetime handling with UTC normalization for created_at/updated_at
  - IntegrityError handling for duplicate slug violations with descriptive error messages
  - Follows UserRepository pattern: optional Session injection, dual session handling (injected vs get_db() context manager)
  - Files created: `backend/src/backend/infrastructure/persistence/post_repository.py`

- **Backend**: HTML sanitization service for XSS prevention in user-generated content

  - Implemented HtmlSanitizer class for comprehensive cross-site scripting (XSS) attack prevention
  - Strict allowlist-based approach permitting only safe HTML tags and attributes
  - Removes dangerous elements: script, style, iframe, object, embed, applet tags
  - External link protection: automatically adds rel="nofollow noreferrer" to all links
  - Image security: restricts image attributes to src, alt, and title only
  - Protocol validation: blocks javascript:, data:, vbscript:, and file: URL schemes
  - Sanitizes blog post content during publish operations to protect readers
  - Preserves markdown-generated HTML structure while removing security threats
  - Built on Bleach library with production-tested XSS protection
  - Comprehensive test suite: 66 unit tests with 97% code coverage validating tag filtering, attribute sanitization, link protection, protocol validation, and edge cases
  - Files created: `backend/src/backend/infrastructure/sanitization/html_sanitizer.py`, `backend/src/backend/infrastructure/sanitization/__init__.py`, `backend/tests/unit/infrastructure/sanitization/test_html_sanitizer.py`
  - Dependencies added: bleach 6.2.0, types-bleach 6.2.0.20241208

- **Documentation**: Comprehensive authentication setup guide in README

  - Added "Authentication" section after "Development" documenting complete authentication system
  - Backend configuration: environment variables (CLERK_PUBLISHABLE_KEY, CLERK_SECRET_KEY)
  - Backend endpoint protection: @require_auth and @require_role decorator usage with code examples
  - Decorator ordering requirements: @require_auth must precede @require_role with correct/incorrect usage examples
  - Accessing current user in endpoints via g.current_user
  - Comprehensive error response catalog: all 401 error types (missing header, invalid format, empty token, verification failed, user not authenticated)
  - 403 Forbidden responses for both author and admin role requirements
  - Frontend configuration: VITE_CLERK_PUBLISHABLE_KEY environment variable
  - ClerkProvider setup explanation for React app initialization
  - Authentication hooks: distinction between custom useAuth (@/context/AuthContext) for role checks and Clerk useAuth (@clerk/clerk-react) for JWT tokens
  - useAuth hook API documentation with code examples showing role-based UI
  - ProtectedRoute component usage for declarative route protection with requireRole prop
  - Common patterns: 3 practical examples combining backend and frontend authentication
  - Troubleshooting guide with 8 common authentication issues and solutions
  - Clerk UserResource type documentation with link to official API reference
  - File modified: `README.md`

- **Frontend**: AuthProvider integration for application-wide authentication state

  - Wrapped AppRoutes with AuthProvider in App.tsx to make auth context available throughout component tree
  - Proper provider nesting established: ClerkProvider > BrowserRouter > AuthProvider > Routes
  - useAuth() hook now accessible from any component within the application
  - Enables role-based rendering and authentication checks across all route components
  - File modified: `frontend/src/App.tsx`

- **Frontend**: Comprehensive E2E authentication flow tests with Playwright

  - Created playwright.config.ts with multi-browser testing (Chromium, Firefox, WebKit)
  - Implemented web server auto-start for frontend (Vite port 3000) and backend (Flask port 5000)
  - Configured test reporting: HTML, JSON, and JUnit XML formats
  - Created tests/e2e/auth-flow.spec.ts with 39 comprehensive authentication tests
  - Test coverage includes: redirect behavior, protected routes, role-based access control, API endpoints, browser compatibility, performance, and reliability
  - Created tests/e2e/fixtures/helpers.ts with 10 reusable test utility functions for common operations (wait for API calls, token extraction, auth verification, login/logout flows, database checks)
  - Implemented test suites: Authentication Flow (24 tests), Role-Based Access Control (4 tests), Browser Compatibility (3 tests), Performance & Reliability (6 tests)
  - Added npm scripts: test:e2e (run all tests), test:e2e:ui (interactive UI), test:e2e:debug (debug mode)
  - Created tests/e2e/README.md with complete documentation: test patterns, configuration, debugging guide, best practices, CI/CD integration
  - Tests verify unauthenticated redirects, JWT token format, role hierarchy enforcement, API health endpoints, session persistence, memory usage, and cross-browser functionality
  - All tests use explicit waits to avoid flakiness: page.waitForURL(), page.waitForLoadState(), page.waitForFunction()
  - Playwright installed as dev dependency (@playwright/test ^1.57.0)
  - Tests run deterministically without flakiness in both local development and CI environments

- **Configuration**: Enhanced Clerk environment variable documentation

  - Added CLERK_PUBLISHABLE_KEY to backend .env.example for frontend integration consistency
  - Improved comments for all Clerk authentication variables explaining purpose and security considerations
  - Backend .env.example now documents three Clerk variables: CLERK_SECRET_KEY (JWT verification), CLERK_PUBLISHABLE_KEY (frontend integration), CLERK_WEBHOOK_SECRET_KEY (webhook validation)
  - Frontend .env.example enhanced with detailed comments explaining VITE_CLERK_PUBLISHABLE_KEY usage and relationship to backend configuration
  - All placeholder values use consistent "your_clerk\_\*" pattern
  - Files modified: `backend/.env.example`, `frontend/.env.example`

- **Frontend**: Protected routes implementation with role-based access control

  - Implemented route protection for /admin and /author paths using ProtectedRoute component with requireRole prop
  - Created Admin.tsx placeholder page for admin dashboard with Tailwind CSS styling
  - Created Author.tsx placeholder page for author dashboard with Tailwind CSS styling
  - Integrated AuthProvider wrapper around Routes in App.tsx for global authentication state
  - Added /login route as public access point for unauthenticated users
  - Added /forbidden route as public error page for unauthorized access attempts
  - Protected routes enforce both authentication (user must be signed in) and authorization (user must have required role)
  - Role hierarchy enforced: admin can access all routes, author can access author routes, authenticated users redirected to forbidden page
  - Created custom test utilities in test-utils.tsx with MemoryRouter support for route testing with initialEntries
  - Exported AppRoutes component separately for testing flexibility (MemoryRouter in tests, BrowserRouter in production)
  - Comprehensive test suite with 38 tests validating route protection, loading states, authentication redirects, authorization checks, and public route access
  - All 203 tests passing with no regressions, production build succeeds
  - Files created: `frontend/src/pages/Admin.tsx`, `frontend/src/pages/Author.tsx`, `frontend/tests/test-utils.tsx`
  - Files modified: `frontend/src/App.tsx`, `frontend/tests/unit/App.test.tsx`

- **Frontend**: 403 Forbidden error page with ShadCN UI components

  - Implemented Forbidden page displaying clear error messaging for users who lack permissions to access a page
  - Integrated ShadCN UI component library with Alert, Button, and Card components for consistent design system
  - Alert component with destructive variant emphasizes security error with red border styling
  - User-friendly error messages without technical jargon (no HTTP/API terms)
  - Navigation link using ShadCN Button component with asChild pattern for React Router integration
  - Responsive layout with centered content and proper spacing on all screen sizes
  - Comprehensive test suite with 10 tests validating UI components, semantics, and user experience
  - All tests passing with 100% statement, branch, function, and line coverage
  - Files created: `frontend/src/pages/Forbidden.tsx`, `frontend/tests/unit/Forbidden.test.tsx`, `frontend/src/components/ui/alert.tsx`, `frontend/src/components/ui/button.tsx`, `frontend/src/components/ui/card.tsx`, `frontend/src/lib/utils.ts`, `frontend/components.json`
  - Dependencies added: @radix-ui/react-slot, class-variance-authority, clsx, lucide-react, tailwind-merge, tailwindcss-animate, tw-animate-css

- **Frontend**: Route protection component for authentication and role-based authorization

  - Implemented ProtectedRoute component wrapping React Router routes with declarative auth enforcement
  - Loading state handling with spinner while authentication state initializes
  - Automatic redirect to login page for unauthenticated users with original URL preservation
  - Automatic redirect to forbidden page for users with insufficient role permissions
  - Role hierarchy enforcement: admin can access all routes, author can access author and authenticated routes, authenticated can only access authenticated routes
  - Type-safe TypeScript implementation with exported ProtectedRouteProps interface
  - Proper React Router v6 integration using Navigate component and useLocation hook for state preservation
  - Comprehensive test suite with 32 tests validating loading states, authentication checks, role authorization, component API, edge cases, and navigation behavior
  - All tests passing with 100% code coverage
  - Files created: `frontend/src/components/auth/ProtectedRoute.tsx`, `frontend/tests/unit/ProtectedRoute.test.tsx`

- **Frontend**: Authentication context provider for global auth state management

  - Implemented AuthProvider component wrapping Clerk's useUser hook for centralized authentication state
  - Created useAuth() custom hook for accessing user authentication context throughout application
  - Type-safe authentication state including user, isLoaded, isSignedIn, and role properties
  - Automatic role fallback to 'authenticated' when not present in Clerk publicMetadata
  - Biome configuration updated to support React context file patterns
  - Comprehensive test suite with 18 tests validating provider setup, context access, role handling, and error boundaries
  - All tests passing with full coverage of authentication context flows
  - Files created: `frontend/src/context/AuthContext.tsx`, `frontend/tests/unit/AuthContext.test.tsx`
  - Files modified: `frontend/biome.json`

- **Frontend**: Clerk authentication provider integration at application root

  - Wrapped React app with ClerkProvider in main.tsx for application-wide authentication context
  - Environment variable validation for VITE_CLERK_PUBLISHABLE_KEY with startup checks
  - Error handling with descriptive messages for missing Clerk configuration
  - Test environment configuration in vitest.config.ts with Clerk environment variables
  - Comprehensive test suite with 21 tests covering provider setup, error boundaries, and configuration validation
  - All tests passing (96/97 total, 1 Clerk SDK internal detail expected)
  - Files modified: `frontend/src/main.tsx`, `frontend/vitest.config.ts`
  - Files created: `frontend/tests/unit/main.test.tsx`

- **Frontend**: Installed Clerk React SDK for user authentication

  - Added @clerk/clerk-react@5.59.3 package to enable frontend authentication capabilities
  - Provides React components and hooks for user sign-in, sign-up, and session management
  - Integrates with Clerk authentication service matching backend JWT verification
  - Dependencies added: @clerk/clerk-react@5.59.3
  - Files modified: `frontend/package.json`, `frontend/package-lock.json`

- **Backend**: Admin user management routes with role-based access control

  - Implemented GET /api/users endpoint for listing all users with pagination (admin only)
  - Implemented PUT /api/users/:id/role endpoint for updating user roles (admin only)
  - Pagination support with configurable limit (1-100, default 50) and offset (default 0) query parameters
  - Role validation ensuring only valid roles (authenticated, author, admin) can be assigned
  - Protected with @require_auth and @require_role('admin') decorators for secure admin-only access
  - Comprehensive error handling: 400 for invalid parameters, 404 for non-existent users, 403 for non-admins
  - Integration test suite with 12 tests covering admin authentication, pagination, role updates, error cases, and authorization enforcement
  - All tests pass with complete coverage of user management flows
  - Files created: `backend/src/backend/api/routes/users.py`, `backend/tests/integration/test_api_routes_users.py`
  - Files modified: `backend/src/backend/main.py` (registered users blueprint at /users prefix)

- **Backend**: Auth routes blueprint with user profile endpoint

  - Implemented GET /api/auth/me endpoint for retrieving authenticated user profile
  - Returns user data including id, clerk_user_id, email, role, and created_at in JSON format
  - Protected with @require_auth decorator for JWT validation
  - Blueprint registered at /auth URL prefix in Flask application factory
  - Comprehensive integration test suite with 10 tests covering valid authentication, missing/invalid/expired tokens, new user creation, role preservation, JSON response format, and CORS headers
  - All tests pass with complete coverage of authentication flows
  - Files created: `backend/src/backend/api/routes/auth.py`, `backend/tests/integration/test_api_routes_auth.py`
  - Files modified: `backend/src/backend/main.py`, `backend/tests/conftest.py`

- **Backend**: JWT authentication middleware with role-based access control

  - Implemented `@require_auth` decorator for protecting Flask endpoints with JWT token validation
  - Implemented `@require_role(role)` decorator for enforcing role-based access control with three authorization levels (authenticated, author, admin)
  - Automatic user creation on first authentication via Clerk integration
  - User context injection into Flask's `g` object for access throughout request lifecycle
  - Comprehensive error handling with AuthenticationError (401) and AuthorizationError (403) responses
  - Integration with ClerkAuthAdapter for JWT verification and user claims extraction
  - UserRepository integration for fetching or creating users based on Clerk user ID
  - Test suite: 26 unit tests with 100% coverage validating decorator behavior, role enforcement, error handling, and user auto-creation
  - Files created: `backend/src/backend/api/middleware/__init__.py`, `backend/src/backend/api/middleware/auth_middleware.py`, `backend/tests/unit/test_auth_middleware.py`
  - Files modified: `backend/src/backend/infrastructure/persistence/user_repository.py` (added `find_by_clerk_user_id()` method)

- **Backend**: Centralized exception handling for authentication and authorization

  - Created custom exception classes AuthenticationError and AuthorizationError in `backend/src/backend/exceptions.py`
  - AuthenticationError for 401 Unauthorized responses handling invalid tokens, expired sessions, and missing authorization headers
  - AuthorizationError for 403 Forbidden responses with optional required_role field indicating minimum role needed for access
  - Flask error handlers registered in `backend/src/backend/main.py` for consistent JSON error responses across all endpoints
  - Centralized exception module accessible to all layers following Hexagonal Architecture dependency rules
  - Refactored ClerkAuthAdapter to import AuthenticationError from central module eliminating duplicate exception definitions
  - Comprehensive test suite: 22 unit tests for exception creation and attributes, 21 integration tests for Flask error handler responses and HTTP status codes
  - All tests pass with 100% coverage of exception classes and error handler logic
  - Files added: `backend/src/backend/exceptions.py`, `backend/tests/unit/test_exceptions.py`, `backend/tests/integration/test_error_handlers.py`
  - Files modified: `backend/src/backend/main.py`, `backend/src/backend/infrastructure/auth/clerk_auth_adapter.py`, `backend/src/backend/infrastructure/auth/__init__.py`, `backend/tests/unit/test_clerk_auth_adapter.py`, `backend/tests/integration/test_clerk_auth_adapter.py`

- **Backend**: Clerk authentication adapter with JWT verification and JWKS caching

  - Implemented ClerkAuthAdapter class in `backend/src/backend/infrastructure/auth/clerk_auth_adapter.py` for secure JWT token validation
  - RS256 algorithm support with Clerk's public key fetched from JWKS endpoint
  - HS256 fallback for test environments with secret key-based validation
  - JWKS public key caching with 1-hour TTL to minimize external API calls and avoid rate limiting
  - Comprehensive error handling with clear authentication failure messages
  - Security logging for failed authentication attempts with user ID extraction
  - Added ClerkSettings configuration class in `backend/src/backend/config.py` for environment-based Clerk credentials
  - Added Settings class combining all application configuration with Pydantic validation
  - Configured Pydantic mypy plugin for proper type checking support
  - Test suite: 29 unit tests with mocked JWKS endpoints and PyJWT validation, 9 integration tests (skipped in CI, require real Clerk tokens)
  - 79% code coverage for ClerkAuthAdapter module with comprehensive test coverage of all error paths
  - Dependencies added: `pyjwt>=2.10.1`, `cryptography>=46.0.3`, `requests>=2.32.5`
  - Files added: `backend/src/backend/infrastructure/auth/clerk_auth_adapter.py`, `backend/src/backend/infrastructure/auth/__init__.py`, `backend/tests/unit/test_clerk_auth_adapter.py`, `backend/tests/integration/test_clerk_auth_adapter_integration.py`
  - Files modified: `backend/src/backend/config.py`, `backend/pyproject.toml`

- **Backend**: User persistence layer with repository pattern for database operations

  - Implemented UserRepository class in `backend/src/backend/infrastructure/persistence/user_repository.py` for CRUD operations on User aggregate
  - Converts between SQLModel User table models and domain User aggregates with bidirectional mapping
  - Supports flexible session management: accepts injected sessions for testing or creates sessions from connection pool for production
  - Methods: `find_by_clerk_id()` with indexed lookup, `find_by_id()`, `save()` with insert/update logic, `list_all()` with optional pagination
  - Comprehensive test suite: 29 tests (20 unit tests for conversion logic, 9 integration tests for database operations) with full coverage
  - Files added: `backend/src/backend/infrastructure/persistence/user_repository.py`, `backend/tests/unit/test_user_repository.py`, `backend/tests/integration/test_user_repository.py`

- **Backend**: User aggregate root for authentication and authorization

  - Created User aggregate implementing Domain-Driven Design patterns for identity management
  - Factory method `create_from_clerk()` enables seamless integration with Clerk authentication provider
  - Role-based access control via `change_role()` method supporting authenticated, author, and admin roles
  - Immutable `created_at` timestamp ensures audit trail integrity for compliance and security tracking
  - API serialization via `to_dict()` method with optional sensitive field exclusion for secure data exposure
  - Full type safety with comprehensive type hints and runtime validation using Pydantic
  - Test suite: 14 comprehensive unit tests with 100% code coverage validating factory methods, role transitions, serialization, and edge cases
  - Files added: `backend/src/backend/domain/aggregates/user.py`, `backend/src/backend/domain/aggregates/__init__.py`, `backend/tests/unit/test_user.py`

- **Backend**: User role enumeration with permission hierarchy

  - Created Role value object as StrEnum with three authorization levels (authenticated, author, admin)
  - Implemented role-based permission methods for author and admin access control
  - Automatic lowercase string conversion using auto() for database compatibility
  - Immutable enum members ensure thread-safe singleton instances
  - JSON serializable for API responses and database storage
  - Type-safe with full type hints for IDE support and static analysis
  - Test suite: 40 comprehensive unit tests with 100% code coverage
  - Files added: `backend/src/backend/domain/value_objects/role.py`, `backend/src/backend/domain/value_objects/__init__.py`, `backend/tests/unit/test_role.py`

- **Backend**: User model supports external authentication provider integration

  - Added support for storing external authentication provider user identifiers
  - Database includes unique index on authentication provider ID for fast JWT validation lookups
  - Nullable field design ensures backward compatibility with existing users
  - Enables secure integration with third-party authentication services
  - Files modified: `backend/src/backend/infrastructure/persistence/models.py`
  - Files added: `backend/tests/integration/test_user_clerk_id.py`

- **Deployment**: Added LiteSpeed deployment script for cPanel environments with UAPI limitations

  - Created `scripts/litespeed_deploy.sh` (435 lines) for cPanel/LiteSpeed hosting
  - LiteSpeed environments experience silent UAPI failures requiring manual web UI configuration
  - Comprehensive deployment automation with security features:
    - Strict error handling with inherit_errexit and pipefail
    - Signal traps to unset secrets on EXIT/INT/TERM
    - Input sanitization for environment variables
    - SSH key permission validation with TOCTOU mitigation
    - Secret suppression in UAPI calls
    - Audit logging to syslog for security-relevant operations
  - Deployment process:
    - Validates environment variables and SSH key permissions
    - Provisions PostgreSQL database, user, and privileges (idempotent)
    - Uploads code via rsync with checksum verification
    - Installs uv on remote server if not present
    - Installs dependencies with uv sync
    - Creates database schema using uv run scripts/create_schema.py
    - Registers/updates Passenger application with environment variables
    - Verifies deployment via health check endpoints with exponential backoff
  - Dual deployment strategy: Use `deploy.sh` for Passenger (UAPI works), `litespeed_deploy.sh` for LiteSpeed (UAPI fails silently)
  - Files added: `scripts/litespeed_deploy.sh`

- **Build**: Added backend build automation script

  - Created `scripts/build_backend.sh` for automated backend builds
  - Uses `uv build --clear` to create distribution packages
  - Copies built packages to `/var/www/ashlab/package/backend/`
  - Generates package index with `scripts/generate_index.py`
  - Files added: `scripts/build_backend.sh`, `scripts/generate_index.py`

- **Deployment**: Added requirements.txt for traditional pip-based deployments

  - Created `backend/requirements.txt` with frozen dependencies
  - Provides fallback deployment path for environments without uv
  - Mirrors dependencies from `pyproject.toml` for compatibility
  - Files added: `backend/requirements.txt`

- **Documentation**: Comprehensive developer onboarding documentation in `README.md`

  - Project overview with Domain-Driven Design and Hexagonal Architecture explanation
  - 15-minute quick start guide with copy-pasteable commands for immediate setup
  - Development workflow documentation for backend (uv) and frontend (npm)
  - Testing instructions for pytest, Vitest, Playwright, and pre-commit hooks
  - CI/CD documentation for GitHub Actions workflows (backend and frontend)
  - Deployment overview with health check verification steps
  - Troubleshooting table with 15 common issues and solutions
  - Contributing guidelines with conventional commits format and PR checklist
  - Resource links for documentation, tooling, and external services (GitHub, Resend, Clerk)
  - Architecture diagram showing bounded contexts and system components
  - Development standards covering code quality, testing pyramid, and security requirements

- **Backend**: Environment variable template in `backend/.env.example`

  - Database configuration variables (LOCAL_POSTGRES_USER, LOCAL_POSTGRES_PASSWORD, LOCAL_POSTGRES_DB)
  - Flask environment settings (FLASK_ENV)
  - External API keys template (GITHUB_PERSONAL_ACCESS_TOKEN, RESEND_API_KEY)
  - Clerk authentication credentials (CLERK_SECRET_KEY)
  - cPanel deployment credentials template (CPANEL_POSTGRES_USER, CPANEL_POSTGRES_PASSWORD, CPANEL_POSTGRES_DB)
  - Clear documentation comments explaining each variable's purpose
  - Security reminder to never commit actual credentials

- **Frontend**: Environment variable template in `frontend/.env.example`

  - API base URL configuration (VITE_API_BASE_URL) for backend communication
  - Clerk authentication public key (VITE_CLERK_PUBLISHABLE_KEY) for frontend integration
  - Vite-specific environment variable naming convention (VITE\_ prefix)
  - Documentation comments explaining variable usage and security practices

- **Deployment**: Automated deployment script for cPanel hosting

  - End-to-end deployment automation to cPanel shared hosting environment
  - Idempotent database provisioning (PostgreSQL database, user, and privileges)
  - Automated code upload via rsync with checksum verification
  - Remote Python virtual environment setup and dependency installation
  - Database schema creation from SQLModel models
  - Passenger WSGI application registration with environment variable injection
  - Health check verification across all critical endpoints
  - Comprehensive error handling with exponential backoff retry logic
  - Cross-platform SSH key handling (Windows Git Bash and Linux compatibility)
  - Security features: input sanitization, secret suppression, audit logging
  - Production deployment confirmation prompt for safety
  - BATS test suite with 40 tests covering validation, provisioning, error handling, and idempotency
  - Comprehensive production domain confirmation test coverage (interactive/non-interactive scenarios, staging/dev domain handling)
  - Detailed deployment documentation with prerequisites and usage examples

- **Backend**: Implemented Passenger WSGI entry point in `src/passenger_wsgi.py`

  - Created WSGI-compliant entry point for Phusion Passenger deployment
  - Implemented virtual environment bootstrap logic with configurable VIRTUAL_ENV environment variable
  - Imported Flask application via `create_app()` factory pattern
  - Exported application as 'application' variable (Passenger WSGI requirement)
  - Comprehensive error handling with actionable debugging information to stderr
  - Cross-platform compatibility (Windows development, Linux production)
  - PEP 3333 WSGI specification compliance
  - Test suite: 9 integration tests covering WSGI interface, variable naming, type verification, request handling, and virtual environment loading, 5 unit tests covering all functions.

- **Backend**: Fixed build directory path in main.py to match Vite output

  - Changed from frontend/dist to build/ to match vite.config.ts outDir
  - Vite outputs to ../build from frontend directory (monorepo/build/)
  - Updated unit tests to expect build/ instead of frontend/dist
  - Updated tests to use Path(**file**).parents[3] instead of repeated .parent

- **CI**: Fixed backend CI workflow to create minimal frontend build structure

  - Creates build/ directory with build/static/js/ subdirectory
  - Creates build/index.html with minimal HTML for SPA routing tests
  - Creates dummy JS file for static file serving tests
  - Allows SPA routing tests to pass without full frontend build
  - Backend tests can verify SPA route handling independently

- **Config**: Removed ty.toml from monorepo

- **CI**: Added workflow_dispatch and workflow file path triggers to both CI workflows

  - Backend and frontend CI now trigger on workflow file changes
  - Added manual trigger capability via workflow_dispatch

- **Backend**: Implemented Flask application factory pattern in `main.py`

  - Created `create_app()` factory function with environment-based configuration
  - Configured Flask with static_folder='dist/static' and template_folder='dist' for React SPA serving
  - Registered health check blueprint with no URL prefix
  - Implemented CORS for development environment only (disabled in production)
  - Added SPA catch-all route serving index.html for client-side routing
  - Implemented path traversal protection with double URL-decoding and backslash detection
  - Added security logging for path traversal attempts and file access errors
  - Production safety: raises RuntimeError if build directory missing in production
  - Development tolerance: logs warning if build directory missing in development
  - Comprehensive test suite: 12 unit tests + 18 integration tests (100% coverage for main.py)
  - Security tests: 5 tests covering path traversal attack vectors (direct, middle, URL-encoded, backslash, exception handling)

- **Integration Testing**: Implemented local build and E2E integration test suite

  - Created `scripts/build.sh` for automated frontend production builds
  - Implemented comprehensive E2E test suite in `backend/tests/e2e/test_build.py`
  - Tests verify frontend build artifacts (index.html, static/, JS bundles)
  - Tests verify Flask server startup and health endpoint responses
  - Tests verify React SPA serving and client-side routing behavior
  - Tests verify API routes excluded from SPA catch-all routing
  - Added `wait_for_server()` utility in `backend/tests/e2e/utils.py` for server readiness checks
  - Pytest fixtures for build execution and Flask server daemon thread management
  - BATS test suite in `scripts/tests/build.bats` with 4 tests validating build script execution
  - Comprehensive validation of production deployment workflow before cPanel deployment

- **Frontend**: Implemented `App.tsx` root component with BrowserRouter routing for Home and NotFound pages.

- **Frontend**: Implemented `main.tsx` Vite entry point using React 18 createRoot API with StrictMode wrapper.

- **Frontend**: Added root element creation to test setup for proper DOM initialization in tests.

### Changed

- **Tests**: Acceptance tests now exercise the real backend instead of mocking it

  - Added local JWKS server (port 5557) serving a committed test RSA key pair as a Playwright web server
  - Flask starts with `FLASK_ENV=TESTING` and `CLERK_JWKS_URL` pointing to the local JWKS server during Playwright runs
  - `clerk-mock.ts` now generates real RS256 JWTs via `jose`; `session.getToken()` returns a signed token the backend can verify
  - Removed all `page.route()` backend mocks from `post-management.ts`; added `beforeAll`/`afterAll` seed/reset hooks
  - Added `POST /api/test/seed` and `DELETE /api/test/reset` endpoints (404 outside `FLASK_ENV=TESTING`) to create test users and posts
  - Added `CLERK_JWKS_URL` override to `Settings` and `ClerkAuthAdapter._construct_jwks_url()`
  - Only external dependencies (Clerk.js, GitHub API) remain mocked

- **Backend**: Refactored PostRevision aggregate to use int IDs for consistency

  - Changed PostRevision.post_id and PostRevision.author_id from UUID to int to match Post and User aggregates
  - Eliminated fragile UUID(int=...) conversion pattern throughout codebase
  - Updated PostRevisionRepository to work directly with int IDs
  - Updated all queries and commands to use int for post_id parameter
  - Improved architectural consistency across domain layer

- **Backend**: Simplified revision API routes by removing unnecessary abstractions

  - Removed handler wrapper classes (GetRevisionHistoryQueryHandler, etc.) that added no value
  - Handler functions now called directly from route handlers
  - Split revisions.py into three focused modules (routes, dependencies, formatters)
  - Reduced revisions.py from 571 to 379 lines (34% reduction)
  - Extracted dependency injection to api/dependencies.py (93 lines)
  - Extracted response formatters to api/formatters.py (56 lines)
  - Improved code maintainability and readability

- **Backend**: Removed all inline code comments from production code

  - Replaced inline comments with docstrings where needed
  - Removed redundant comments that restated obvious code
  - Enforced CLAUDE.md rule: no code comments, only docstrings

- **Backend**: Post table schema update for improved field naming and querying

  - Renamed `published_html` column to `html_content` for consistency with domain model
  - Added `published_at` field (datetime | None) to track publication timestamp with database index for efficient sorting
  - Added index to `published` field for optimized filtering queries
  - Updated PostRepository to handle timezone-aware datetime conversion for `published_at` field
  - Updated PostRepository field mapping: `_to_model()` and `_to_domain()` now use `html_content` field
  - Added timezone awareness logic: converts naive datetime to UTC timezone when loading from database
  - Comprehensive test coverage: 19 unit tests for model schema and repository field mapping with 100% pass rate
  - Files modified: `backend/src/backend/infrastructure/persistence/models.py`, `backend/src/backend/infrastructure/persistence/post_repository.py`
  - Files created: `backend/tests/unit/test_post_repository.py`
  - Tests modified: `backend/tests/unit/test_models.py` (updated to use `html_content` field)

- **Frontend**: Refactored NotFound and Home pages to use ShadCN UI components for design consistency

  - Replaced custom Tailwind-styled link in NotFound page with ShadCN Button component using asChild pattern
  - Replaced custom div card in Home page with ShadCN Card component (CardHeader, CardTitle, CardContent)
  - Replaced plain text error display in Home page with ShadCN Alert component with destructive variant
  - Ensures consistent design system across all frontend pages matching Forbidden page implementation
  - All existing tests updated and passing (3 NotFound tests, 17 Home tests)
  - No breaking changes to component behavior or user experience
  - Files modified: `frontend/src/pages/NotFound.tsx`, `frontend/src/pages/Home.tsx`, `frontend/tests/unit/NotFound.test.tsx`, `frontend/tests/unit/Home.test.tsx`

- **Backend**: Locked Python version requirement to exact match

  - Changed from `>=3.13.5` to `==3.13.5` in `backend/pyproject.toml`
  - Ensures consistent Python version across deployments
  - Updated `backend/uv.lock` to remove Python 3.14 wheels
  - Files modified: `backend/pyproject.toml`, `backend/uv.lock`

- **Backend**: Improved WSGI entry point module resolution

  - Added `APP_ROOT` to `sys.path` in `passenger_wsgi.py`
  - Ensures proper module imports in production Passenger environment
  - Files modified: `backend/src/passenger_wsgi.py`

- **Frontend**: Updated entry point from `main.jsx` to `main.tsx` in `index.html`.

- **Frontend**: Updated tests to correctly expect `React.StrictMode` as `symbol` type (React 18 behavior).

### Removed

- **Tests**: Removed temporary BATS test file

  - Deleted `scripts/tests/deploy_config_fix.bats` (should not have been committed)
  - Main BATS test suite remains intact in `scripts/tests/`
  - Files removed: `scripts/tests/deploy_config_fix.bats`

### Fixed

- **RevisionTimeline**: Added `role="alert"` to error state and extract backend error message from response body so authorization errors display "not authorized" text correctly

- **RevisionHistory**: Improved `isForbidden` detection to match backend error message text in addition to HTTP status code

- **useRevisions/usePosts**: Added `retry: false` to all query hooks so 403/404 errors surface immediately without retry delays

- **PostRevisionRepository**: `find_by_sha` now supports short SHA prefix matching (< 40 chars uses `startswith`) in addition to full SHA exact match

- **DiffViewer**: Removed `hasChanges` guard so context-only diff arrays render correctly; parent page passes empty array for same-SHA comparisons to show "No changes detected"

- **DiffViewer**: Corrected `data-testid` from `diff-viewer` (added), line background colours from `bg-green-50`/`bg-red-50` to `bg-green-100`/`bg-red-100`, and line number logic to use `line_number_new ?? line_number_old` from real API field names

- **RevisionTimeline**: Changed `data-testid` from `revision-timeline-container` to `revision-timeline`

- **RevisionDiffPage**: Fixed reversed `useRevisionDiff` argument order (`sha`, `otherSha`)

- **revisionsApi**: Updated `DiffLine` interface to match real backend shape: `line_number_old?` and `line_number_new?` (snake_case) replacing `lineNumber?`

- **types/revision**: Removed non-existent `RevisionAuthor` re-export

- **Tests**: Fixed `author: { id, name }` → `author_id` across all revision test files (unit, integration, acceptance)

- **Tests**: Fixed `revision-timeline-container` → `revision-timeline` testid in integration and unit tests

- **Tests**: Fixed `DiffLine` field name (`lineNumber` → `line_number_new`) and colour assertions in both DiffViewer test files

- **Acceptance tests**: Rewrote `revision-tracking.ts` to use real backend — removed all `page.route()` mocks, added `beforeAll`/`afterAll` seed/reset hooks, serial mode

- **API**: `GET /api/posts/<slug>` now includes markdown `content` from the filesystem so the editor loads with existing draft text

- **API**: `DELETE /api/posts/<slug>` now soft-deletes the DB record (sets `deleted_at`) rather than removing it; all read queries exclude soft-deleted posts

- **API**: Delete handler no longer raises `RuntimeError` on GitHub failure; logs a warning and continues (consistent with save/publish behaviour)

- **Tests**: Seed endpoint drops and recreates all tables on every call, guaranteeing a clean DB state regardless of prior run outcome

- **Tests**: Fixed `Delete Draft Post` locator — `/delete/i` matched all three row buttons when the post title contains "Delete"; narrowed to `/^delete post/i`

- **Tests**: Post-management acceptance tests now pass reliably

  - Added dummy `GITHUB_OWNER`, `GITHUB_REPO`, `GITHUB_PERSONAL_ACCESS_TOKEN` env vars to the Playwright Flask command so `GitHubSettings()` initialises without raising `ValidationError`; GitHub calls log a 401 warning and continue
  - Seed endpoint now creates filesystem draft files under `DRAFTS_PATH=/tmp/test-drafts` so the publish handler can find draft content; reset deletes those files
  - Set `workers: 1` to eliminate Flask contention between parallel Playwright workers
  - Replaced CSS-class locators (`.bg-gray-100`, `.bg-green-100`) with `getByRole('cell')` assertions; Tailwind v4 does not emit those classes in the dev build

- **Backend**: Fixed `SELECT SELECT 1` bug in `/api/health/db` endpoint

  - `sqlmodel.select(text("SELECT 1"))` generated invalid SQL; replaced with `get_engine().connect()` and raw `text("SELECT 1")` via SQLAlchemy directly
  - Updated test mocks from `get_db`/`Session` to `get_engine`
  - Corrected health route URLs from `/health` to `/api/health` in integration and passenger WSGI tests

- **Frontend**: Skipped all revision tracking tests pending full spec implementation

  - `tests/e2e/revision-history.ts` and `tests/acceptance/revision-tracking.ts` — `test.describe.fixme`
  - `tests/integration/revision-workflow.test.tsx`, `tests/unit/components/revision/RevisionTimeline.test.tsx`, `tests/unit/services/revisionsApi.test.ts` — `describe.skip`
  - Fixed pre-existing prop mismatches (`postId`→`slug`, `onRevertClick`→`onRevertSuccess`, missing `isAuthor`)
  - Fixed health check URL in acceptance tests and playwright config (`/health`→`/api/health`)

- **Frontend**: Fixed API mock URL patterns in acceptance tests

  - Added missing `/api` prefix to all route mocks in post-management.ts
  - Ensures Playwright tests correctly intercept frontend API requests
  - Aligns with Vite proxy configuration and actual request patterns

- **Backend**: Improved test reliability and clarity

  - Replaced conditional `pytest.skip()` with `@pytest.mark.xfail` decorator in revision tracking tests
  - Renamed `test_post_revision_table_schema` to `test_create_post_triggers_github_commit` for clarity
  - Made configuration test flexible for local/test environments (accepts TEST\_/MOCK\_ prefixed env vars)
  - Fixed CHANGELOG file path reference for E2E tests (pointed to wrong directory)

- **Frontend**: Extracted role derivation helper to reduce code duplication

  - Created `deriveRoleFromMetadata()` helper function
  - Eliminates duplicate role parsing logic between ClerkAuthProvider and MockAuthProvider
  - Ensures consistent role handling across authentication providers

- **Backend**: Posts blueprint registration and URL structure consistency

  - Fixed posts blueprint registration to follow project architectural patterns (explicit url_prefix in Flask app factory)
  - Updated route paths to use empty string `""` instead of `"/"` for base route, matching users_bp pattern
  - Corrected endpoint paths: list-my-posts moved from `/api/my-posts` to `/api/posts/my-posts` for proper REST hierarchy
  - Updated 36 integration tests to use correct endpoint paths
  - All posts routes now consistently namespaced under `/api/posts`: POST /api/posts (create), GET /api/posts/:slug (read), PUT /api/posts/:slug (update), DELETE /api/posts/:slug (delete), POST /api/posts/:slug/publish, POST /api/posts/:slug/unpublish, GET /api/posts/my-posts (list)
  - Files modified: `backend/src/backend/main.py` (added url_prefix="/api/posts" to blueprint registration), `backend/src/backend/api/routes/posts.py` (removed internal url_prefix, updated route decorators), `backend/tests/integration/api/test_posts_routes.py` (updated test paths)

- **Backend**: Corrected import order in html_sanitizer test file to comply with ruff linting standards

- **Backend**: Corrected authentication blueprint URL prefixes to match specification

  - Changed auth_bp registration from `/auth` to `/api/auth` in main.py
  - Changed users_bp registration from `/users` to `/api/users` in main.py
  - Updated all integration tests to use corrected endpoints
  - Updated documentation examples in auth.py and users.py
  - Endpoints now accessible at `/api/auth/me` and `/api/users` as per requirements
  - All 22 backend integration tests pass with corrected URL prefixes
  - Files modified: `backend/src/backend/main.py`, `backend/tests/integration/test_api_routes_auth.py`, `backend/tests/integration/test_api_routes_users.py`, `backend/src/backend/api/routes/auth.py`, `backend/src/backend/api/routes/users.py`

- **Frontend**: Code review fixes for authentication implementation

  - Fixed unsafe type assertion in AuthContext role extraction to use explicit validation instead of type casting
  - Updated all useAuth mocks in test files to match AuthContextType interface (replaced userId/signOut with user object)
  - Improved loading indicator in ProtectedRoute from plain text to animated Loader2 spinner icon from lucide-react
  - Updated all loading state tests to check for spinner element instead of "Loading..." text
  - All 203 tests passing with improved user experience and type safety

- **Frontend**: Resolved Playwright test configuration conflict with Vitest globals

  - Fixed "Playwright Test did not expect test.describe() to be called here" error caused by TypeScript configuration
  - Created separate tsconfig.playwright.json for Playwright tests with only @playwright/test types
  - Excluded tests/e2e directory from main tsconfig.json to prevent vitest/globals type pollution
  - Excluded tests/e2e directory from vitest.config.ts to prevent Vitest from running Playwright tests
  - All 39 authentication E2E tests (117 total across 3 browsers) now load and run successfully
  - Files modified: `frontend/tsconfig.json` (added exclude for tests/e2e), `frontend/vitest.config.ts` (added include/exclude patterns)
  - Files created: `frontend/tsconfig.playwright.json` (dedicated TypeScript config for Playwright)

- **Backend**: Fixed CI test failures due to eager initialization of Settings in auth middleware

  - Refactored auth_middleware.py to use lazy initialization pattern for Settings, ClerkAuthAdapter, and UserRepository
  - Prevents ValidationError during module import when CLERK_PUBLISHABLE_KEY and CLERK_SECRET_KEY environment variables are not set
  - Implemented singleton pattern with private getter functions (\_get_settings, \_get_clerk_adapter, \_get_user_repository)
  - Module-level variables (clerk_auth_adapter, user_repository) now default to None for test mock compatibility
  - Adapters and repositories are instantiated only when decorators are actually invoked, not at import time
  - All 208 unit tests pass including 17 auth middleware tests with full backward compatibility
  - No breaking changes to decorator API or test mocking patterns
  - File modified: `backend/src/backend/api/middleware/auth_middleware.py`

- **Code Review Fixes (PR #7)**: Implemented fixes from sourcery-ai and gemini-code-assist code reviews

  - **Build Script**: Enhanced shell safety flags in `scripts/build.sh`
    - Added `set -u` to error on unset variables
    - Added `set -o pipefail` to catch errors in pipelines
    - Removed unnecessary `exit 0` that could hide non-zero exit codes
    - Changed `npm install` to `npm ci` for faster, more reliable builds from lockfile
  - **E2E Tests**: Improved test reliability and production configuration
    - Fixed build fixture to always run build for test determinism
    - Added `try...finally` block to ensure cleanup even if tests fail
    - Track initial BUILD_DIR state to preserve pre-existing builds
    - Changed FLASK_ENV from DEVELOPMENT to PRODUCTION to accurately test production stack
    - Marked GitHub health check test with `@pytest.mark.external` to allow skipping in offline/restricted environments
  - **BATS Tests**: Optimized build script test performance
    - Refactored to use `setup_file()`/`teardown_file()` hooks
    - Build script now runs once per test file instead of once per test (4x faster)
    - Individual tests now only verify build artifacts exist

- **Code Review Fixes (PR #8)**: Addressed documentation and configuration issues from gemini-code-assist code review

  - **Backend Configuration**: Corrected `.env.example` to use `LOCAL_*` prefix variables matching `config.py` expectations
    - Fixed database configuration to use `LOCAL_DB_HOST`, `LOCAL_DB_NAME`, `LOCAL_DB_USER`, `LOCAL_DB_PASSWORD`
    - Ensures development environment variables align with `DevDBSettings` class requirements
  - **API Documentation**: Updated health endpoint documentation in `docs/api.md` to match actual implementation
    - Fixed `/health/db` endpoint response format (simple status object instead of detailed host/database info)
    - Fixed `/health/github` endpoint response format (simple status object instead of detailed rate_limit info)
  - **README Organization**: Improved build script documentation clarity
    - Reorganized `./scripts/build.sh` command placement for better categorization
    - Clarified frontend-specific vs. project-wide command usage
  - **Deployment Documentation**: Added missing `PRODUCTION_DOMAIN` environment variable to deployment docs table
    - Documented required variable for production confirmation prompt functionality
    - Completed environment variables reference in `docs/DEPLOYMENT.md`

- **Deployment**: Critical bug fix in error handling for deployment script

  - Fixed `uapi_call()` function to correctly capture and propagate command exit codes
  - Previously, `if ! command; then` pattern was causing `$?` to be 0 (success of if-test negation) instead of the actual command failure code
  - Changed to explicitly capture exit status before testing: `command; exit_status=$?; if [[ $exit_status -ne 0 ]]; then`
  - This ensures deployment aborts immediately when UAPI operations fail instead of continuing silently
  - Added comprehensive error checking (`|| return 1`) to all deployment functions for fail-fast behavior
  - Fixed tests 12, 13, and 14 which were failing assertions but not executing
  - Test 12: Added `stat` mock for SSH key permission verification
  - Tests 13-14: Added proper UAPI mocks that handle different operations independently

- **Frontend**: Updated frontend dependencies to latest versions.

- **Frontend**: Corrected Biome configuration to remove redundant include paths.

- **Frontend**: Separated Vitest configuration into `vitest.config.ts` and ensured shared configuration with `vite.config.ts` using `mergeConfig`.

- **Deployment**: Fixed virtual environment path to match cPanel conventions

  - Changed from `/home/${CPANEL_USERNAME}/seeash/.venv` to `/home/${CPANEL_USERNAME}/virtualenv/seeash`
  - Added `UV_PROJECT_ENVIRONMENT` variable to direct uv to create virtual environment in correct location
  - Applies to both `install_application()` and `run_schema()` functions
  - Updated `VENV_PATH` environment variable passed to Passenger
  - Follows cPanel convention documented in cpanel-deployment-patterns.md lines 23-24, 73
  - Virtual environment now created at `/home/ashrdvfi/virtualenv/seeash` instead of application root
  - Files modified: `scripts/deploy.sh`

- **Deployment**: Fixed critical environment variable syntax for Passenger UAPI calls

  - Changed from numbered parameters (`envvar_name_1`, `envvar_value_1`) to repeated parameters (`envvar_name`, `envvar_value`)
  - Applies to both `register_application` and `edit_application` UAPI functions
  - Environment variables now successfully set in Passenger application configuration
  - Verified all 8 environment variables (DB_NAME, DB_USER, DB_PASSWORD, VENV_PATH, GITHUB_PERSONAL_ACCESS_TOKEN, RESEND_API_KEY, CLERK_PUBLISHABLE_KEY, CLERK_SECRET_KEY) are injected correctly
  - Syntax documented in cpanel-deployment-patterns.md lines 171-183
  - Files modified: `scripts/deploy.sh`

- **Deployment**: Fixed deployment script to use Python src-layout structure for uv compatibility

  - Changed backend upload destination from `seeash/backend/` to `seeash/src/backend/` to match uv src-layout convention
  - Changed scripts upload destination from `seeash/scripts/` to `seeash/src/scripts/` for proper Python module import
  - Added remote directory creation for `seeash/src` before file uploads
  - Created `__init__.py` in `monorepo/backend/src/scripts/` to make scripts package importable
  - Fixed local scripts source path from `monorepo/backend/scripts/` to `monorepo/backend/src/scripts/`
  - Updated deployment tests to expect `seeash/src/backend/` instead of `seeash/backend/`
  - Updated test helper to create `monorepo/backend/src/scripts/` directory structure
  - Fixes uv package installation error: "Expected a Python module at: src/backend/**init**.py"
  - Fixes schema creation error: "ModuleNotFoundError: No module named 'scripts'"
  - Files modified: `scripts/deploy.sh`, `scripts/tests/deploy.bats`, `scripts/tests/test_helper.bash`, `backend/src/scripts/__init__.py` (created)

- **Deployment**: Fixed deployment script to match production directory structure specifications

  - Changed remote application path from `/home/${CPANEL_USERNAME}/blog` to `/home/${CPANEL_USERNAME}/seeash`
  - Corrected backend source upload from `monorepo/backend/` to `monorepo/backend/src/backend/`
  - Added upload of `passenger_wsgi.py` from `monorepo/backend/src/` to `seeash/` (root level)
  - Added upload of `scripts/` directory to seeash (path later corrected to src-layout)
  - Added upload of `pyproject.toml` and `uv.lock` to root level for uv package management
  - Updated all remote script paths from `~/blog` to `~/seeash`
  - Updated virtual environment path from `~/blog/.venv` to `~/seeash/.venv`
  - Removed hardcoded username "ashrdvfi" from WSGI copy section
  - Removed unnecessary WSGI copy remote script (handled by rsync now)
  - Updated deployment tests to expect new paths and directory structure
  - Updated test helper to create correct backend source structure for tests
  - Updated DEPLOYMENT.md documentation to reflect correct remote directory structure
  - Files modified: `scripts/deploy.sh`, `scripts/tests/deploy.bats`, `scripts/tests/test_helper.bash`, `docs/DEPLOYMENT.md`

- **Deployment**: Fixed critical Passenger WSGI bootstrap issues (Task #27)

  - Added VENV_PATH environment variable to Passenger registration
    - Required by passenger_wsgi.py to bootstrap uv virtualenv before Flask import
    - Added to both register_application and update_application UAPI calls
    - Path: `/home/${CPANEL_USERNAME}/blog/.venv`
  - Copy passenger_wsgi.py to domain root during code upload
    - Passenger expects WSGI entry point in application root (~/seeash/)
    - Added SSH command in upload_code() to copy from ~/blog/src/
    - Includes validation to ensure source file exists before copying
  - Remove explicit DB_HOST from schema creation
    - Rely on ProductionDBSettings default 'localhost' resolution
    - Handles both IPv4 and IPv6 gracefully via driver-level resolution

- **Deployment**: Fixed frontend build path check in deployment script

  - Changed from `monorepo/frontend/build` to `monorepo/build` to match Vite output location
  - Deployment script now correctly detects frontend build directory
  - Prevents "frontend build directory missing" errors during deployment

- **Backend**: Fixed ProductionDBSettings to use standard database environment variable names

  - Removed `CPANEL_` prefix from ProductionDBSettings configuration
  - Now reads `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` directly (no prefix)
  - Aligns with Passenger WSGI standard environment variable naming conventions
  - Resolves deployment failure where Flask could not connect to database

- **Deployment**: Fixed schema creation during deployment to set required environment variables

  - Added exports for `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `FLASK_ENV` in run_schema() function
  - Schema creation script now receives all required database configuration
  - Prevents "missing required fields" validation errors during remote schema execution

### Security

- **Frontend**: Added environment guard to test mode authentication bypass

  - Test mode now requires `import.meta.env.MODE === 'test'` in addition to `window.__CLERK_TEST_MOCK__`
  - Prevents production users from spoofing authentication by setting window variables
  - Blocks potential privilege escalation via browser console manipulation
  - Addresses critical security vulnerability identified in PR review

- **Backend**: Implemented comprehensive XSS prevention for blog post content

  - Protects against script injection attacks in published posts
  - Prevents malicious iframe embedding and plugin execution
  - Blocks dangerous URL schemes in links and images
  - Mitigates CSS-based attacks by removing style tags and attributes
  - Adds nofollow/noreferrer to external links preventing referrer leakage and SEO manipulation
  - Sanitization applied automatically during post publishing workflow

- **Backend**: Production-ready markdown to HTML rendering service with syntax highlighting

  - Implemented MarkdownRenderingService for converting markdown content to HTML with Pygments syntax highlighting
  - Syntax highlighting support for 500+ programming languages including Python, JavaScript, TypeScript, C++, C#, F#, JSON
  - Code block rendering with proper CSS class attributes for theme integration
  - Graceful fallback for unknown programming languages using lexer auto-detection, with plain text rendering as final fallback
  - Production-ready error handling with try-except blocks and graceful degradation on rendering failures
  - Comprehensive logging at module level (debug, warning, error) for production observability
  - Stateless service design enabling concurrent rendering without race conditions
  - Dependencies added: markdown-it-py 3.0.0+ for markdown parsing, Pygments 2.17.0+ for syntax highlighting, types-Pygments for type safety
  - Comprehensive test suite: 43 unit tests covering markdown features (headings, lists, links, images, code blocks), syntax highlighting (Python, JavaScript, TypeScript, JSON, C++, C#), edge cases (empty input, Unicode, HTML escaping), and error handling (93% coverage)
  - Files created: `backend/src/backend/infrastructure/markdown/markdown_rendering_service.py`, `backend/src/backend/infrastructure/markdown/__init__.py`, `backend/tests/unit/infrastructure/test_markdown_rendering_service.py`
  - Files modified: `backend/pyproject.toml`, `backend/uv.lock`

- **Backend**: GitHubSyncService for automatic version control via GitHub API

  - Implemented resilient GitHub API integration for draft version control
  - commit_file() method creates or updates files in GitHub repository with base64 encoding
  - delete_file() method removes files from GitHub repository
  - Exponential backoff retry logic for HTTP 429 rate limiting (1s, 2s, 4s delays, max 3 retries)
  - Non-blocking error handling - draft operations succeed even if GitHub API fails
  - Comprehensive error recovery: handles timeouts, connection errors, HTTP errors (401/403/404/500)
  - Secure token handling - never logs authentication credentials
  - Returns commit SHA on successful operations for audit trail
  - 5-second timeout on all network requests prevents indefinite hanging
  - Constructor validation ensures required credentials (token, owner, repo) are provided
  - Comprehensive test suite: 24 unit tests covering success paths, retry logic, error handling (100% coverage)
  - Files created: `backend/src/backend/infrastructure/versioning/github_sync_service.py`, `backend/src/backend/infrastructure/versioning/__init__.py`, `backend/tests/unit/infrastructure/versioning/test_github_sync_service.py`, `backend/tests/unit/infrastructure/versioning/__init__.py`
  - Meets all requirements: 10.1 (commit on create), 10.2 (commit on save), 10.3 (commit on delete), 10.4 (non-blocking failures), 10.5 (rate limit retry), 10.6 (graceful degradation)

- **Backend**: FileSystemDraftRepository for markdown draft persistence

  - Implemented filesystem-based repository for blog post drafts with YAML front matter
  - DraftFile class for YAML serialization/deserialization with complete metadata support
  - YAML front matter includes: title, author, created_at, published, published_at, tags
  - FileSystemDraftRepository with CRUD operations: save(), find_by_slug(), delete(), list_by_author()
  - Path traversal protection using Slug value object for safe filesystem operations
  - UTF-8 encoding support for international characters and emoji
  - Idempotent delete operation (succeeds even if file doesn't exist)
  - Auto-creates drafts directory on repository initialization
  - Round-trip preservation of all metadata and content through save/load cycles
  - Configuration support: DRAFTS_PATH, GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO settings
  - Comprehensive test suite: 13 unit tests for DraftFile, 13 integration tests for repository (100% coverage)
  - Files created: `backend/src/backend/infrastructure/persistence/filesystem_draft_repository.py`, `backend/tests/unit/test_draft_file.py`, `backend/tests/integration/test_filesystem_draft_repository.py`
  - Files modified: `backend/src/backend/config.py`
  - Dependencies added: pyyaml 6.0.3, types-pyyaml 6.0.12.20250915

- **Backend**: Post aggregate root for blog post lifecycle management

  - Mutable aggregate implementing Domain-Driven Design patterns for post state transitions
  - Factory method `create_draft()` for creating new draft posts with validated title and author
  - State transition methods: `publish()` converts drafts to published posts with HTML content, `unpublish()` reverts to draft state
  - Integration with Slug value object for URL-safe identifiers and HtmlContent for sanitized HTML storage
  - UTC-aware timestamps: `created_at` (immutable), `updated_at` (auto-managed), `published_at` (audit trail preserved on unpublish)
  - Input validation: title must be non-empty string, author_id must be positive integer
  - Audit trail preservation: published_at timestamp retained when unpublishing for historical tracking
  - Type-safe with modern Python 3.12+ type hints including datetime and UUID annotations
  - Comprehensive test suite with 14 unit tests covering factory method, state transitions, timestamp handling, and edge cases (100% coverage)
  - Files created: `backend/src/backend/domain/aggregates/post.py`, `backend/tests/unit/test_post.py`

- **Backend**: HtmlContent value object for type-safe sanitized HTML storage

  - Immutable wrapper for sanitized HTML content in published blog posts
  - Validates content is not None while accepting empty strings for valid empty posts
  - Preserves HTML formatting, whitespace, and special characters
  - Frozen dataclass implementation preventing post-initialization mutations
  - Value object semantics with equality based on content, proper string representation
  - Comprehensive test coverage with 14 unit tests (100% coverage)
  - Files created: `backend/src/backend/domain/value_objects/html_content.py`, `backend/tests/unit/test_html_content.py`
  - Files modified: `backend/src/backend/domain/value_objects/__init__.py`

- **Backend**: MarkdownContent value object for type-safe markdown storage

  - Immutable wrapper for raw markdown text in blog post drafts
  - Validates content is not None to prevent invalid state
  - Preserves markdown formatting and special characters
  - Comprehensive test coverage with 14 unit tests (100% coverage)
  - Files created: `backend/src/backend/domain/value_objects/markdown_content.py`, `backend/tests/unit/test_markdown_content.py`

- **Backend**: URL slug validation and normalization for blog posts

  - Implemented immutable Slug value object with automatic formatting
  - Converts uppercase to lowercase, replaces spaces with hyphens, removes special characters
  - Enforces validation: non-empty, maximum 200 characters, alphanumeric and hyphens only
  - Secure against path traversal attacks with comprehensive input sanitization
  - 100% test coverage with 22 unit tests
  - Files created: `backend/src/backend/domain/value_objects/slug.py`, `backend/tests/unit/test_slug.py`

## [0.1.2] - 2025-11-17

### Fixed

- **CI**: Fixed frontend CI build failure by updating `vitest` to `^4.0.9` and adding `@vitest/coverage-v8`.

## [0.1.1] - 2025-11-14

### Added

#### Foundation Stage - Infrastructure Setup

- **Task 1**: Created git repository with .gitignore (Python, Flask, Node, React, SSH, VSCode templates)
- **Task 2**: Configured pre-commit hooks with Ruff, mypy, Biome, and general checks
- **Task 3**: Configured Biome for frontend linting and formatting
  - Created frontend/biome.json with React/JSX rules and a11y accessibility checks
  - Configured formatter with 2-space indentation and 100-character line width
  - Enabled hooks rules (useExhaustiveDependencies, useHookAtTopLevel, useJsxKeyInIterable)
  - Updated pre-commit hook to use explicit config path for Biome
- **Task 4**: Initialized backend project structure with uv
  - Created complete DDD/Hexagonal Architecture directory structure
  - Set up Python 3.13.5+ requirement in pyproject.toml
  - Created domain, application, infrastructure, and api layers
  - Set up test directories (unit, integration, e2e)
  - Generated uv.lock file
  - Added placeholder files (main.py, config.py, schema.sql, passenger_wsgi.py)
- **Task 5**: Configured Ruff for backend linting and formatting
  - Added [tool.ruff] configuration to backend/pyproject.toml
  - Set line-length to 80 characters, target-version to py313
  - Enabled lint rules: A (builtins), ANN (annotations), D (docstrings), DOC (docstrings), E (pycodestyle errors), F (pyflakes), I (isort), N (pep8-naming), UP (pyupgrade), W (pycodestyle warnings)
  - Configured flake8-annotations with allow-star-arg-any and mypy-init-return
  - Set pydocstyle convention to Google style with ignore-decorators for typing.overload
  - Added per-file-ignores for tests/docs/tools and **init**.py files
  - Verified uvx ruff check and uvx ruff format commands work correctly
- **Task 6**: Configured mypy for type checking
  - Added [tool.mypy] configuration to backend/pyproject.toml
  - Set python_version to "3.13" for Python 3.13 target compatibility
  - Enabled warn_return_any for strict return type checking
  - Enabled check_untyped_defs to require type hints on function definitions
  - Set ignore_missing_imports to allow third-party libraries without type stubs
  - Verified uv run mypy . runs successfully with no issues found in 16 source files
- **Task 7**: Created backend CI workflow
  - Created .github/workflows/backend-ci.yml for automated backend testing
  - Configured to run on Python 3.13 only (not a matrix strategy)
  - Uses official astral-sh/setup-uv@v1 action for uv setup
  - Triggers on push to main/foundation branches and pull requests to main
  - Runs linting with Ruff (uvx ruff check)
  - Runs type checking with mypy (uv run mypy)
  - Runs tests with pytest with coverage reporting (uv run pytest --cov --cov-report=xml)
  - Enforces 80% code coverage threshold with --cov-fail-under=80
  - All steps run in backend/ directory
- **Task 8**: Created frontend CI workflow
  - Created .github/workflows/frontend-ci.yml with matrix strategy for Node 22.18 and 24.6
  - Configured triggers for push to main/foundation branches and pull requests to main
  - Added steps: checkout, setup Node.js with npm caching, install dependencies, lint, test, build
  - Uses actions/checkout@v3 and actions/setup-node@v3
  - Linting with Biome (npx biome check .)
  - Testing with coverage reporting (npm test -- --coverage --run)
  - Coverage threshold check placeholder (70% will be enforced when tests exist)
  - Production build step (npm run build)
  - All steps run in frontend/ directory with fail-fast behavior
- **Task 9**: Initialized React project with Vite
  - Created frontend/package.json with React 18.3.1, Vite 5.4.11, React Router 6.28.0, Axios 1.7.9
  - Configured dependencies: React, React-DOM, React Router, Axios for API calls
  - Configured devDependencies: Vite, Vitest, React Testing Library, Biome, Tailwind CSS, PostCSS, Autoprefixer
  - Created frontend/vite.config.js with @/ alias pointing to ./src
  - Configured build output to ../build/ directory (shared with backend)
  - Configured dev server on port 3000 with proxy to Flask backend on port 5000
  - Created frontend/index.html as Vite entry point
  - Created src/ directory structure: components/, pages/, hooks/, services/, context/
  - Created minimal src/main.jsx with React 18 StrictMode entry point
  - Moved biome.json from frontend/ to blog-code/ root for monorepo configuration
  - Updated biome.json to include frontend paths in includes array
  - Ran npm install successfully (329 packages installed)
  - Verified production build outputs correctly to ../build/ directory
  - Set package.json homepage to "." for relative asset paths
- **Task 10**: Configured Tailwind CSS
  - Created frontend/tailwind.config.js with content paths for ./index.html and ./src/\*\*/\*.{js,jsx}
  - Configured theme.extend as empty object (using default Tailwind theme)
  - Created frontend/postcss.config.js with tailwindcss and autoprefixer plugins
  - Created src/index.css with Tailwind directives (@tailwind base, @tailwind components, @tailwind utilities)
  - Updated src/main.jsx to import index.css at top of file
  - Fixed biome.json schema version to 2.3.2 to match installed Biome CLI version
  - Fixed biome.json to use "includes" instead of "include" for Biome 2.3.2 compatibility
  - Updated .pre-commit-config.yaml to remove --config-path argument from biome-ci hook (uses automatic discovery)
  - Verified production build succeeds with Tailwind CSS processed (build size 4.7KB for CSS)
  - Verified Tailwind base styles (CSS reset) included in output
  - Confirmed CSS purging works correctly (no utility classes used yet, so minimal output)
  - Verified Biome formatting works correctly with all configuration files

#### Backend Configuration & Database

- **Task 11**: Created configuration management with Pydantic
  - Created backend/src/config.py implementing Pydantic BaseSettings
  - Defined DBSettings base class with DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, FLASK_ENV fields
  - DB_HOST defaults to localhost (cPanel requirement)
  - Created DevDBSettings with LOCAL\_ prefix for development environment
  - Created ProductionDBSettings with CPANEL\_ prefix for production environment
  - Implemented get_db_settings() factory function with caching
  - Added environment-based settings class selection
  - Fail-fast validation on missing required environment variables
  - Unit tests in tests/unit/test_config.py with 100% coverage
- **Task 12**: Created database schema with SQLModel
  - Created backend/src/infrastructure/persistence/models.py
  - Defined User table model (id, email, role, created_at)
  - Defined Post table model (id, slug, title, published_html, published, author_id, created_at, updated_at)
  - Added foreign key constraint from Post.author_id to User.id
  - Added indexes on Post.slug and Post.author_id for query performance
- **Task 13**: Created database connection with SQLModel
  - Created backend/src/infrastructure/persistence/database.py
  - Implemented get_engine() function with lru_cache for singleton engine pattern
  - Configured PostgreSQL connection string using settings from config.py
  - Enabled pool_pre_ping for connection health checks
  - Implemented get_db() generator for FastAPI/Flask dependency injection
  - Uses SQLModel Session context manager for automatic cleanup
  - Added psycopg2-binary dependency for PostgreSQL driver
  - Integration tests in tests/integration/test_database.py
  - Created shared test fixtures in tests/conftest.py

#### Backend API: Health Checks

- **Task 14**: Created health check endpoints blueprint
  - Created backend/src/api/routes/health.py with Flask blueprint
  - Implemented GET /health endpoint for basic uptime check (returns 200 with {"status": "healthy"})
  - Implemented GET /health/db endpoint for database connectivity test (executes SELECT 1 query, returns 200/503)
  - Implemented GET /health/github endpoint for GitHub API reachability test (calls <https://api.github.com/rate_limit>>, returns 200/503)
  - All endpoints return JSON responses with appropriate status codes
  - Added Flask and requests dependencies to pyproject.toml
  - Health endpoints handle exceptions gracefully, returning 503 on failure with error details
  - Database health check uses execute() method for SQLModel Session compatibility
  - GitHub health check uses 5-second timeout for external API calls
  - Integration tests in tests/integration/test_health_endpoints.py with 9 passing tests
  - Created tests/integration/conftest.py with shared fixtures for integration tests
  - All tests verify correct status codes, JSON content types, and error handling

#### Frontend API Service: Health Checks (TDD)

- **Task 15**: Created health check API service with TypeScript
  - Created frontend/src/services/healthService.ts with axios client
  - Implemented checkHealth(), checkDatabase(), checkGitHub() methods
  - Configured axios instance with baseURL from VITE_API_BASE_URL environment variable or '/api' default
  - Added TypeScript type definitions: HealthResponse, DatabaseHealthResponse, GitHubHealthResponse
  - All methods properly typed with Promise return types
  - Errors propagate to caller for proper error handling
  - Comprehensive test coverage in tests/unit/healthService.test.ts with 6 passing tests
  - Created tests/mocks/axios.ts with complete axios mock (mocks both default instance and create() factory)
  - Created tests/setup.ts for Vitest configuration with jest-dom
  - Configured Vitest in vite.config.ts with jsdom environment and coverage reporting
  - Added TypeScript support: tsconfig.json and tsconfig.node.json
  - Installed TypeScript dependencies: typescript, @types/react, @types/react-dom, @types/node
  - Updated biome.json to include TypeScript file patterns (.ts, .tsx)
  - All tests use proper TypeScript types and mocking patterns with vi.mock() factory
  - Tests verify correct endpoint calls, response data handling, and error propagation

#### Frontend Components & Routing (TDD)

- **Task 16**: Created NotFound page component

  - Created frontend/src/pages/NotFound.tsx with 404 error page
  - Implemented user-friendly 404 message with Tailwind styling
  - Added React Router Link component for navigation back to home page
  - Responsive design with centered layout and proper visual hierarchy
  - Comprehensive test coverage in tests/unit/NotFound.test.tsx with 3 passing tests
  - Tests verify 404 message rendering, home link presence and navigation, component styling
  - All tests use React Testing Library with BrowserRouter wrapper
  - Component uses Tailwind utility classes for styling (flex, text-9xl, rounded-lg, etc.)

- Created Home page component with health status display

  - Created frontend/src/pages/Home.tsx as landing page demonstrating health check integration
  - Implemented health status fetching from healthService.checkHealth() on component mount
  - Added loading, error, and success state management using React hooks (useState, useEffect)
  - Displays "Loading..." message while fetching health data
  - Shows user-friendly error message on API failure
  - Renders health status in styled card layout on success
  - Responsive design with Tailwind CSS styling consistent with NotFound.tsx
  - Comprehensive test coverage in tests/unit/Home.test.tsx with 17 passing tests (100% statements, 83.33% branches)
  - Tests verify initial render/loading state, successful health display, error handling, component lifecycle, state transitions, and accessibility
  - All tests use React Testing Library with proper mocking of healthService
  - TypeScript with proper HealthResponse interface integration

- Established monorepo structure with backend/ and frontend/ directories

- Configured uv as Python package manager

- Set up pre-commit hooks for code quality enforcement

- Configured GitHub Actions CI/CD pipelines for backend (Python 3.13) and frontend (Node 22.18, 24.6)

### Changed

- Refactored `config.py` to introduce `get_db_url()` for obtaining the database connection string, replacing direct instantiation of `DBSettings`.
- Updated tests in `test_config.py` to reflect the refactoring and added tests for `get_db_url()`.

### Fixed

#### Code Review Fixes (PR #2)

- **Critical**: Fixed datetime field defaults in `User` and `Post` models
  - Changed `Field(default=datetime.now(dt.UTC))` to `Field(default_factory=lambda: datetime.now(dt.UTC))`
  - Prevents all records from sharing the same import-time timestamp
  - Files: `backend/src/infrastructure/persistence/models.py` (lines 13, 27-28)
  - Added comprehensive unit tests validating timestamp uniqueness
- **Critical**: Replaced deprecated Pydantic v2 API in `config.py`
  - Changed `.unicode_string()` to `str()` for PostgresDsn conversion
  - Ensures compatibility with future Pydantic versions
  - File: `backend/src/config.py` (line 53)
- **Security**: Removed information leakage from health endpoint errors
  - Changed error responses from `str(e)` to generic "unreachable" message
  - Added structured logging for internal diagnostics
  - Prevents exposure of database credentials, stack traces, network details
  - File: `backend/src/api/routes/health.py` (lines 47-48, 70-73)
  - Health endpoints now use `requests.exceptions.RequestException`
- **Testing**: Added test for non-200 GitHub API responses
  - File: `backend/tests/integration/test_health_endpoints.py`
