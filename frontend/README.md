# Frontend Documentation

React-based frontend for the blog platform with Clerk authentication, React Query state management, and Tailwind CSS styling. This document covers post management UI components, hooks, and API integration patterns.

## Table of Contents

- [Overview](#overview)
- [Post Management](#post-management)
- [Components](#components)
- [Hooks](#hooks)
- [API Client](#api-client)
- [Complete Workflows](#complete-workflows)
- [Testing](#testing)
- [Accessibility](#accessibility)
- [Security](#security)

## Overview

### Tech Stack

| Layer           | Technology           | Purpose                             |
| :-------------- | :------------------- | :---------------------------------- |
| **Framework**   | React 18             | UI component library                |
| **State**       | React Query          | Server state management and caching |
| **Auth**        | Clerk                | Authentication and JWT token mgmt   |
| **Routing**     | React Router v6      | Client-side routing                 |
| **Styling**     | Tailwind CSS         | Utility-first CSS framework         |
| **Markdown**    | @uiw/react-md-editor | Markdown editing with live preview  |
| **HTTP Client** | Axios                | API request library                 |
| **Testing**     | Vitest + Playwright  | Unit and E2E testing                |
| **Linting**     | Biome                | Unified linting and formatting      |

### Architecture

```text
src/
├── components/
│   ├── post/              # Post management components
│   │   ├── MarkdownEditor.tsx    # Markdown editing with preview
│   │   ├── PreviewPane.tsx       # Read-only markdown rendering
│   │   └── PostForm.tsx          # Create post form with validation
│   └── ui/                # Shared UI components (shadcn/ui)
├── pages/
│   ├── PostEditor.tsx     # Edit draft page
│   ├── MyPosts.tsx        # Author's post list
│   └── PublicPost.tsx     # Public post view
├── hooks/
│   ├── usePosts.ts        # React Query hooks for posts
│   ├── useAuth.ts         # Authentication context hook
│   └── queryKeys.ts       # Query key factory for caching
├── services/
│   └── postsApi.ts        # API client for post endpoints
└── context/
    └── AuthContext.tsx    # Auth provider with role-based logic
```

### Data Flow

```text
User Action
    ↓
Component Event Handler
    ↓
React Query Hook (usePosts)
    ↓
Get JWT Token (Clerk useAuth)
    ↓
API Client (postsApi)
    ↓
HTTP Request to Backend
    ↓
React Query Cache Update
    ↓
Component Re-render
```

## Post Management

### Features

- **Draft Creation**: Create new posts with slug and title validation
- **Markdown Editing**: Full-featured markdown editor with live preview
- **Save Drafts**: Save markdown content to filesystem + GitHub
- **Publish/Unpublish**: Convert drafts to published posts with HTML rendering
- **List Management**: Filter, paginate, and manage posts
- **Delete**: Permanently remove draft posts
- **Public Viewing**: View published posts without authentication

### State Management

React Query manages all server state with automatic caching, background refetching, and optimistic updates:

**Cache Keys:**

- `['posts', 'draft', slug]` - Single draft by slug
- `['posts', 'my-posts']` - User's post list (all)
- `['posts', 'my-posts', { filter, page, limit }]` - Filtered/paginated list
- `['posts', 'public', slug]` - Public post view

**Cache Invalidation:**

| Mutation        | Invalidates                          |
| :-------------- | :----------------------------------- |
| `createDraft`   | `['posts', 'my-posts']`              |
| `saveDraft`     | `['posts', 'draft', slug]`, my-posts |
| `publishPost`   | `['posts', 'draft', slug]`, my-posts |
| `unpublishPost` | `['posts', 'draft', slug]`, my-posts |
| `deleteDraft`   | `['posts', 'draft', slug]`, my-posts |

## Components

### MarkdownEditor

Full-featured markdown editor with live preview, keyboard shortcuts, and XSS prevention.

**Location:** `src/components/post/MarkdownEditor.tsx`

**Purpose:** Provides a controlled markdown editing interface with split-pane view (editor + preview) and Ctrl+S/Cmd+S save shortcuts.

**Props:**

```typescript
interface MarkdownEditorProps {
  value: string              // Current markdown content
  onChange: (content: string) => void  // Callback when content changes
  onSave?: () => void | Promise<void>  // Optional save callback (triggered by Ctrl+S)
  className?: string         // Optional CSS classes for container
}
```

**Features:**

- Split-pane markdown editor with live preview
- Syntax highlighting in preview pane
- Keyboard shortcut: Ctrl+S (Windows/Linux) or Cmd+S (Mac) triggers save
- XSS prevention via rehype-sanitize plugin
- Controlled component pattern (parent manages state)
- Accessible with keyboard navigation

**Example Usage:**

```tsx
import { useState } from 'react'
import { MarkdownEditor } from '@/components/post/MarkdownEditor'
import { useSaveDraft } from '@/hooks/usePosts'

function DraftEditor({ slug }: { slug: string }) {
  const [content, setContent] = useState('')
  const saveDraft = useSaveDraft()

  const handleSave = async () => {
    await saveDraft.mutateAsync({ slug, content })
  }

  return (
    <MarkdownEditor
      value={content}
      onChange={setContent}
      onSave={handleSave}
    />
  )
}
```

**Markdown Features Supported:**

- Headings (H1-H6)
- Bold, italic, strikethrough
- Lists (ordered, unordered, nested)
- Links and images
- Code blocks with syntax highlighting
- Blockquotes
- Tables
- Horizontal rules

**Security:**

Previews are sanitized client-side using rehype-sanitize to prevent XSS attacks. Script tags, inline event handlers, and dangerous protocols are stripped.

### PreviewPane

Client-side markdown preview component with syntax highlighting.

**Location:** `src/components/post/PreviewPane.tsx`

**Purpose:** Renders markdown as HTML for preview during editing or display. Does not require backend rendering.

**Props:**

```typescript
interface PreviewPaneProps {
  markdown: string           // Raw markdown to render
  isLoading?: boolean        // Show loading spinner
  error?: string | null      // Error message to display
  className?: string         // Optional CSS classes
}
```

**Features:**

- Client-side markdown rendering with @uiw/react-markdown-preview
- Syntax highlighting for code blocks (Prism-based)
- XSS protection via rehype-sanitize
- Loading and error states
- Prose styling with Tailwind typography

**Example Usage:**

```tsx
import { PreviewPane } from '@/components/post/PreviewPane'

function PostPreview({ markdown }: { markdown: string }) {
  return (
    <div className="grid grid-cols-2 gap-4">
      <textarea value={markdown} onChange={...} />
      <PreviewPane markdown={markdown} />
    </div>
  )
}
```

**With Loading/Error States:**

```tsx
import { PreviewPane } from '@/components/post/PreviewPane'
import { useDraft } from '@/hooks/usePosts'

function DraftPreview({ slug }: { slug: string }) {
  const { data, isLoading, error } = useDraft(slug)

  if (isLoading) {
    return <PreviewPane markdown="" isLoading={true} />
  }

  if (error) {
    return <PreviewPane markdown="" error={error.message} />
  }

  return <PreviewPane markdown={data?.content || ''} />
}
```

### PostForm

Form component for creating new posts with real-time slug validation.

**Location:** `src/components/post/PostForm.tsx`

**Purpose:** Collects slug and title for new post creation with client-side validation matching backend rules.

**Props:**

```typescript
interface PostFormProps {
  onSubmit: (data: { slug: string; title: string }) => void
  initialValues?: { slug?: string; title?: string }
  onChange?: (data: { slug: string; title: string }) => void
  className?: string
}
```

**Features:**

- Real-time slug normalization (lowercase, hyphens, alphanumeric only)
- Client-side validation (non-empty, max 200 chars)
- Accessible form with ARIA attributes
- Submit button disabled until valid
- Error messages shown inline

**Slug Normalization Rules:**

1. Convert to lowercase
2. Replace spaces with hyphens
3. Remove special characters (keep only `a-z`, `0-9`, `-`)
4. Collapse consecutive hyphens
5. Trim leading/trailing hyphens
6. Enforce 200 character limit

**Example Usage:**

```tsx
import { PostForm } from '@/components/post/PostForm'
import { useCreateDraft } from '@/hooks/usePosts'
import { useNavigate } from 'react-router-dom'

function CreatePostPage() {
  const createDraft = useCreateDraft()
  const navigate = useNavigate()

  const handleSubmit = async (data: { slug: string; title: string }) => {
    await createDraft.mutateAsync(data)
    navigate(`/edit/${data.slug}`)
  }

  return (
    <div>
      <h1>Create New Post</h1>
      <PostForm onSubmit={handleSubmit} />
      {createDraft.error && <p>Error: {createDraft.error.message}</p>}
    </div>
  )
}
```

**Validation Examples:**

| Input                              | Normalized Output             | Valid? | Error Message                       |
| :--------------------------------- | :---------------------------- | :----- | :---------------------------------- |
| `My First Post`                    | `my-first-post`               | ✓      | -                                   |
| `Hello World!!!`                   | `hello-world`                 | ✓      | -                                   |
| `123-test`                         | `123-test`                    | ✓      | -                                   |
| \`\` (empty)                       | \`\` (empty)                  | ✗      | Slug is required                    |
| `a-very-long-slug-...` (250 chars) | `a-very-long-...` (200 chars) | ✗      | Slug must not exceed 200 characters |

## Pages

### PostEditor

Main page for editing blog post drafts with markdown editor and preview.

**Location:** `src/pages/PostEditor.tsx`

**Route:** `/edit/:slug`

**Purpose:** Full-featured post editing interface with save, publish, and preview functionality.

**Features:**

- Markdown editor with real-time preview
- Save draft button + Ctrl+S keyboard shortcut
- Publish button with confirmation dialog
- Toggle preview pane (desktop: side-by-side, mobile: toggle view)
- Loading state while fetching draft
- Error state for draft not found
- Success message after save (auto-dismiss after 3s)
- Accessible with keyboard navigation and screen reader support

**Workflow:**

1. Component mounts with slug from URL
2. `useDraft(slug)` fetches draft from API
3. Display loading spinner while fetching
4. Render editor with draft content
5. User edits markdown in editor
6. User saves with button or Ctrl+S
7. `useSaveDraft` mutation with optimistic update
8. Success message shown and auto-dismissed
9. User publishes with button
10. Confirmation dialog shown
11. `usePublishPost` mutation
12. Navigate to public post page

**Example Navigation:**

```tsx
import { Link } from 'react-router-dom'

function MyPostsList({ posts }) {
  return (
    <ul>
      {posts.map(post => (
        <li key={post.slug}>
          <Link to={`/edit/${post.slug}`}>{post.title}</Link>
        </li>
      ))}
    </ul>
  )
}
```

**Error Handling:**

| Error State           | UI Response                                      |
| :-------------------- | :----------------------------------------------- |
| Draft not found (404) | Error alert: "Draft not found"                   |
| Network error         | Error alert with error message                   |
| Save fails            | Error alert below header, save button re-enabled |
| Publish fails         | Error alert below header, dialog closes          |

### MyPosts

Author's post management page with filtering, pagination, and CRUD actions.

**Location:** `src/pages/MyPosts.tsx`

**Route:** `/my-posts`

**Purpose:** List and manage all posts belonging to the authenticated user.

**Features:**

- Filter tabs: All / Drafts / Published
- Pagination controls (20 posts per page)
- Post table with columns: Title, Status, Last Updated, Slug, Actions
- Action buttons: Edit (navigate to editor), View (published only), Delete
- Delete confirmation dialog
- Loading state with spinner
- Error state with user-friendly message
- Empty state: "No posts found"

**Filter Behavior:**

- **All**: Shows both drafts and published posts
- **Drafts**: Shows only unpublished posts
- **Published**: Shows only published posts

**Workflow:**

1. Component mounts, fetches posts with `useMyPosts(filter, page)`
2. Display posts in table
3. User clicks filter button → update filter state → refetch with new filter
4. User clicks pagination → update page state → refetch with new page
5. User clicks Delete → confirmation dialog opens
6. User confirms → `useDeleteDraft` mutation → cache invalidated → list refreshes

**Example Usage in Route:**

```tsx
import { Route } from 'react-router-dom'
import MyPosts from '@/pages/MyPosts'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'

<Route
  path="/my-posts"
  element={
    <ProtectedRoute requireRole="author">
      <MyPosts />
    </ProtectedRoute>
  }
/>
```

**Pagination:**

- Default: 20 posts per page
- Pagination controls show: "Page X of Y"
- Previous/Next buttons disabled at boundaries
- Changing filter resets to page 1

**Date Formatting:**

Dates displayed as `M/D/YYYY` format (e.g., `1/20/2026`).

### PublicPost

Public-facing page for viewing published blog posts.

**Location:** `src/pages/PublicPost.tsx`

**Route:** `/posts/:slug`

**Purpose:** Display published posts to all users (no authentication required).

**Features:**

- Fetches published post via public API endpoint
- Displays post title, author, publication date, and HTML content
- Renders sanitized HTML with `dangerouslySetInnerHTML`
- Error state: "Post not found" for 404 or unpublished posts
- Back to home link
- Accessible with semantic HTML
- Responsive design with max-width container

**Workflow:**

1. Component mounts with slug from URL
2. `usePublicPost(slug)` fetches from public endpoint (no auth)
3. Display loading spinner while fetching
4. Render post with title, metadata, and content
5. Error: show "Post not found" alert with back link

**Example Usage:**

```tsx
import { Link } from 'react-router-dom'

function RecentPosts({ posts }) {
  return (
    <ul>
      {posts.map(post => (
        <li key={post.slug}>
          <Link to={`/posts/${post.slug}`}>{post.title}</Link>
        </li>
      ))}
    </ul>
  )
}
```

**Date Formatting:**

Publication date displayed as `Month Day, Year` format (e.g., `January 20, 2026`).

**Security:**

HTML content is rendered with `dangerouslySetInnerHTML` but is already sanitized server-side during the publish process with Bleach. No client-side sanitization needed.

## Hooks

All hooks use React Query for server state management with automatic caching, background refetching, and optimistic updates.

### useDraft

Fetch a single draft by slug.

**Location:** `src/hooks/usePosts.ts`

**Signature:**

```typescript
function useDraft(slug: string): UseQueryResult<PostResponse, Error>
```

**Parameters:**

- `slug` (string): Post slug identifier

**Returns:**

React Query result object with:

- `data`: Post data (or undefined if loading/error)
- `isLoading`: Boolean loading state
- `error`: Error object if fetch failed
- `refetch`: Function to manually refetch

**Authentication:**

Requires JWT token from Clerk. Automatically retrieves token via `useAuth().getToken()`.

**Example Usage:**

```tsx
import { useDraft } from '@/hooks/usePosts'

function DraftEditor({ slug }: { slug: string }) {
  const { data: draft, isLoading, error } = useDraft(slug)

  if (isLoading) return <p>Loading draft...</p>
  if (error) return <p>Error: {error.message}</p>
  if (!draft) return <p>Draft not found</p>

  return (
    <div>
      <h1>{draft.title}</h1>
      <p>Last updated: {new Date(draft.updated_at).toLocaleString()}</p>
    </div>
  )
}
```

**Response Type:**

```typescript
interface PostResponse {
  id: number
  slug: string
  title: string
  author_id: number
  html_content: string
  content: string | null
  published: boolean
  published_at: string | null
  created_at: string
  updated_at: string
}
```

### useMyPosts

Fetch paginated list of user's posts with optional filtering.

**Location:** `src/hooks/usePosts.ts`

**Signature:**

```typescript
function useMyPosts(
  filter?: PostFilter,
  page?: number,
  limit?: number
): UseQueryResult<ListPostsResponse, Error>
```

**Parameters:**

- `filter` (optional): Filter posts by status: `'all'` | `'drafts'` | `'published'` (default: undefined, treated as `'all'`)
- `page` (optional): Page number (1-indexed, default: 1)
- `limit` (optional): Posts per page (default: 20)

**Returns:**

React Query result with `data`, `isLoading`, `error`, `refetch`.

**Authentication:**

Requires JWT token from Clerk.

**Example Usage:**

```tsx
import { useState } from 'react'
import { useMyPosts } from '@/hooks/usePosts'
import type { PostFilter } from '@/services/postsApi'

function PostList() {
  const [filter, setFilter] = useState<PostFilter>('all')
  const [page, setPage] = useState(1)
  const { data, isLoading, error } = useMyPosts(filter, page, 20)

  if (isLoading) return <p>Loading posts...</p>
  if (error) return <p>Error: {error.message}</p>

  return (
    <div>
      <div>
        <button onClick={() => setFilter('all')}>All</button>
        <button onClick={() => setFilter('drafts')}>Drafts</button>
        <button onClick={() => setFilter('published')}>Published</button>
      </div>

      <ul>
        {data?.posts.map(post => (
          <li key={post.slug}>{post.title}</li>
        ))}
      </ul>

      <div>
        Page {data?.page} of {data?.total_pages}
        <button onClick={() => setPage(p => p - 1)} disabled={page <= 1}>
          Previous
        </button>
        <button onClick={() => setPage(p => p + 1)} disabled={page >= (data?.total_pages || 1)}>
          Next
        </button>
      </div>
    </div>
  )
}
```

**Response Type:**

```typescript
interface ListPostsResponse {
  posts: PostResponse[]
  total_count: number
  total_pages: number
  page: number
  limit: number
}
```

### usePublicPost

Fetch a single published post by slug (no authentication required).

**Location:** `src/hooks/usePosts.ts`

**Signature:**

```typescript
function usePublicPost(slug: string): UseQueryResult<PublicPostResponse, Error>
```

**Parameters:**

- `slug` (string): Post slug identifier

**Returns:**

React Query result with `data`, `isLoading`, `isError`.

**Authentication:**

None required. Public endpoint.

**Example Usage:**

```tsx
import { usePublicPost } from '@/hooks/usePosts'

function PublicPostView({ slug }: { slug: string }) {
  const { data: post, isLoading, isError } = usePublicPost(slug)

  if (isLoading) return <p>Loading...</p>
  if (isError || !post) return <p>Post not found</p>

  return (
    <article>
      <h1>{post.title}</h1>
      <p>By {post.author} on {new Date(post.published_at).toLocaleDateString()}</p>
      <div dangerouslySetInnerHTML={{ __html: post.html_content }} />
    </article>
  )
}
```

**Response Type:**

```typescript
interface PublicPostResponse {
  slug: string
  title: string
  author: string
  html_content: string
  published_at: string
}
```

### useCreateDraft

Create a new draft post.

**Location:** `src/hooks/usePosts.ts`

**Signature:**

```typescript
function useCreateDraft(): UseMutationResult<
  PostResponse,
  Error,
  { slug: string; title: string }
>
```

**Parameters:**

Mutation accepts object with:

- `slug` (string): URL-safe post slug
- `title` (string): Post title

**Returns:**

React Query mutation result with:

- `mutate`: Synchronous mutation function
- `mutateAsync`: Promise-based mutation function
- `isPending`: Boolean loading state
- `error`: Error object if mutation failed

**Authentication:**

Requires JWT token from Clerk.

**Cache Invalidation:**

On success, invalidates `['posts', 'my-posts']` to refresh post lists.

**Example Usage:**

```tsx
import { useCreateDraft } from '@/hooks/usePosts'
import { useNavigate } from 'react-router-dom'

function CreatePostButton() {
  const createDraft = useCreateDraft()
  const navigate = useNavigate()

  const handleCreate = async () => {
    try {
      const draft = await createDraft.mutateAsync({
        slug: 'my-new-post',
        title: 'My New Post'
      })
      navigate(`/edit/${draft.slug}`)
    } catch (error) {
      console.error('Failed to create draft:', error)
    }
  }

  return (
    <button onClick={handleCreate} disabled={createDraft.isPending}>
      {createDraft.isPending ? 'Creating...' : 'Create Post'}
    </button>
  )
}
```

**Error Handling:**

| Error Code | Cause                                 | User Message                         |
| :--------- | :------------------------------------ | :----------------------------------- |
| 400        | Invalid slug format or missing fields | Invalid slug or title                |
| 401        | Not authenticated                     | Authentication required              |
| 403        | User does not have author role        | Author role required                 |
| 409        | Slug already exists                   | A post with this slug already exists |

### useSaveDraft

Save draft content with optimistic updates.

**Location:** `src/hooks/usePosts.ts`

**Signature:**

```typescript
function useSaveDraft(): UseMutationResult<
  PostResponse,
  Error,
  { slug: string; content: string }
>
```

**Parameters:**

Mutation accepts object with:

- `slug` (string): Post slug identifier
- `content` (string): Markdown content to save

**Returns:**

React Query mutation result with `mutate`, `mutateAsync`, `isPending`, `error`.

**Authentication:**

Requires JWT token from Clerk.

**Optimistic Updates:**

Immediately updates cached draft with new content before API response. Rolls back on error.

**Cache Invalidation:**

On success, invalidates:

- `['posts', 'draft', slug]`
- `['posts', 'my-posts']`

**Example Usage:**

```tsx
import { useState } from 'react'
import { useSaveDraft } from '@/hooks/usePosts'

function DraftEditor({ slug }: { slug: string }) {
  const [content, setContent] = useState('')
  const saveDraft = useSaveDraft()

  const handleSave = async () => {
    try {
      await saveDraft.mutateAsync({ slug, content })
      alert('Draft saved successfully!')
    } catch (error) {
      alert('Failed to save draft')
    }
  }

  return (
    <div>
      <textarea value={content} onChange={e => setContent(e.target.value)} />
      <button onClick={handleSave} disabled={saveDraft.isPending}>
        {saveDraft.isPending ? 'Saving...' : 'Save Draft'}
      </button>
      {saveDraft.error && <p>Error: {saveDraft.error.message}</p>}
    </div>
  )
}
```

**Optimistic Update Behavior:**

1. User clicks Save
2. UI immediately shows updated `updated_at` timestamp
3. API request sent in background
4. On success: cache updated with server response
5. On error: cache rolled back to previous state, error shown

### usePublishPost

Publish a draft post.

**Location:** `src/hooks/usePosts.ts`

**Signature:**

```typescript
function usePublishPost(): UseMutationResult<PostResponse, Error, string>
```

**Parameters:**

Mutation accepts `slug` (string).

**Returns:**

React Query mutation result with `mutate`, `mutateAsync`, `isPending`, `error`.

**Authentication:**

Requires JWT token from Clerk.

**Cache Invalidation:**

On success, invalidates:

- `['posts', 'draft', slug]`
- `['posts', 'my-posts']`

**Example Usage:**

```tsx
import { usePublishPost } from '@/hooks/usePosts'
import { useNavigate } from 'react-router-dom'

function PublishButton({ slug }: { slug: string }) {
  const publishPost = usePublishPost()
  const navigate = useNavigate()

  const handlePublish = async () => {
    const confirmed = confirm('Are you sure you want to publish this post?')
    if (!confirmed) return

    try {
      await publishPost.mutateAsync(slug)
      navigate(`/posts/${slug}`)
    } catch (error) {
      alert('Failed to publish post')
    }
  }

  return (
    <button onClick={handlePublish} disabled={publishPost.isPending}>
      {publishPost.isPending ? 'Publishing...' : 'Publish'}
    </button>
  )
}
```

**Backend Processing:**

On publish, the backend:

1. Reads markdown from filesystem
2. Renders to HTML with syntax highlighting
3. Sanitizes HTML with Bleach
4. Stores in database
5. Updates `published: true` and `published_at` timestamp
6. Commits to GitHub

### useUnpublishPost

Unpublish a published post.

**Location:** `src/hooks/usePosts.ts`

**Signature:**

```typescript
function useUnpublishPost(): UseMutationResult<PostResponse, Error, string>
```

**Parameters:**

Mutation accepts `slug` (string).

**Returns:**

React Query mutation result with `mutate`, `mutateAsync`, `isPending`, `error`.

**Authentication:**

Requires JWT token from Clerk.

**Cache Invalidation:**

On success, invalidates:

- `['posts', 'draft', slug]`
- `['posts', 'my-posts']`

**Example Usage:**

```tsx
import { useUnpublishPost } from '@/hooks/usePosts'

function UnpublishButton({ slug }: { slug: string }) {
  const unpublishPost = useUnpublishPost()

  const handleUnpublish = async () => {
    const confirmed = confirm('Are you sure you want to unpublish this post?')
    if (!confirmed) return

    try {
      await unpublishPost.mutateAsync(slug)
      alert('Post unpublished')
    } catch (error) {
      alert('Failed to unpublish post')
    }
  }

  return (
    <button onClick={handleUnpublish} disabled={unpublishPost.isPending}>
      {unpublishPost.isPending ? 'Unpublishing...' : 'Unpublish'}
    </button>
  )
}
```

**Behavior:**

- Sets `published: false` in database
- Removes post from public view
- Preserves `published_at` timestamp and HTML content
- Post still accessible to author via `/edit/:slug`

### useDeleteDraft

Delete a draft post permanently.

**Location:** `src/hooks/usePosts.ts`

**Signature:**

```typescript
function useDeleteDraft(): UseMutationResult<void, Error, string>
```

**Parameters:**

Mutation accepts `slug` (string).

**Returns:**

React Query mutation result with `mutate`, `mutateAsync`, `isPending`, `error`.

**Authentication:**

Requires JWT token from Clerk.

**Cache Invalidation:**

On success:

- Removes `['posts', 'draft', slug]` from cache
- Invalidates `['posts', 'my-posts']`

**Example Usage:**

```tsx
import { useDeleteDraft } from '@/hooks/usePosts'
import { useNavigate } from 'react-router-dom'

function DeleteButton({ slug }: { slug: string }) {
  const deleteDraft = useDeleteDraft()
  const navigate = useNavigate()

  const handleDelete = async () => {
    const confirmed = confirm('Are you sure you want to delete this draft? This action cannot be undone.')
    if (!confirmed) return

    try {
      await deleteDraft.mutateAsync(slug)
      navigate('/my-posts')
    } catch (error) {
      alert('Failed to delete draft')
    }
  }

  return (
    <button onClick={handleDelete} disabled={deleteDraft.isPending}>
      {deleteDraft.isPending ? 'Deleting...' : 'Delete Draft'}
    </button>
  )
}
```

**Restrictions:**

- Cannot delete published posts (must unpublish first)
- Deletes from filesystem, database, and GitHub
- Operation is permanent

## API Client

### postsApi

Axios-based API client for post management endpoints.

**Location:** `src/services/postsApi.ts`

**Base URL:** Configured via `VITE_API_BASE_URL` environment variable (default: `/api`).

**Authentication:** All methods except `getPublicPost` require JWT token passed as parameter.

### Methods

#### createDraft

Create a new draft post.

**Signature:**

```typescript
async createDraft(slug: string, title: string, token: string): Promise<PostResponse>
```

**HTTP:** `POST /posts`

**Request Body:**

```json
{
  "slug": "my-post",
  "title": "My Post Title"
}
```

**Response:** `PostResponse` object with `id`, `slug`, `title`, `published: false`.

**Errors:**

- 400: Invalid slug format
- 401: Unauthorized
- 403: Author role required
- 409: Slug already exists

#### getDraft

Retrieve a draft by slug.

**Signature:**

```typescript
async getDraft(slug: string, token: string): Promise<PostResponse>
```

**HTTP:** `GET /posts/:slug`

**Response:** `PostResponse` object.

**Errors:**

- 401: Unauthorized
- 403: Cannot access another author's draft
- 404: Draft not found

#### saveDraft

Save markdown content to draft.

**Signature:**

```typescript
async saveDraft(slug: string, content: string, token: string): Promise<SaveDraftResponse>
```

**HTTP:** `PUT /posts/:slug`

**Request Body:**

```json
{
  "content": "# My Post\n\nMarkdown content here..."
}
```

**Response:**

```json
{
  "message": "Draft saved successfully",
  "slug": "my-post"
}
```

**Errors:**

- 400: Missing content
- 401: Unauthorized
- 403: Cannot edit another author's draft
- 404: Draft not found

#### deleteDraft

Delete a draft permanently.

**Signature:**

```typescript
async deleteDraft(slug: string, token: string): Promise<void>
```

**HTTP:** `DELETE /posts/:slug`

**Response:** 204 No Content

**Errors:**

- 400: Post is published (must unpublish first)
- 401: Unauthorized
- 403: Cannot delete another author's draft
- 404: Draft not found

#### publishPost

Publish a draft post.

**Signature:**

```typescript
async publishPost(slug: string, token: string): Promise<PostResponse>
```

**HTTP:** `POST /posts/:slug/publish`

**Response:** `PostResponse` object with `published: true`, `published_at` timestamp.

**Errors:**

- 400: Post already published
- 401: Unauthorized
- 403: Cannot publish another author's post
- 404: Draft not found

#### unpublishPost

Unpublish a published post.

**Signature:**

```typescript
async unpublishPost(slug: string, token: string): Promise<PostResponse>
```

**HTTP:** `POST /posts/:slug/unpublish`

**Response:** `PostResponse` object with `published: false`.

**Errors:**

- 400: Post is not published
- 401: Unauthorized
- 403: Cannot unpublish another author's post
- 404: Post not found

#### listMyPosts

List user's posts with filtering and pagination.

**Signature:**

```typescript
async listMyPosts(
  filter?: PostFilter,
  page?: number,
  limit?: number,
  token: string
): Promise<ListPostsResponse>
```

**HTTP:** `GET /posts/my-posts?filter={filter}&page={page}&limit={limit}`

**Query Parameters:**

- `filter`: `'all'` | `'drafts'` | `'published'`
- `page`: 1-indexed page number
- `limit`: Results per page (1-100)

**Response:**

```json
{
  "posts": [/* PostResponse objects */],
  "total_count": 42,
  "total_pages": 3,
  "page": 1,
  "limit": 20
}
```

**Errors:**

- 400: Invalid query parameters
- 401: Unauthorized

#### getPublicPost

Fetch a published post (public endpoint, no auth).

**Signature:**

```typescript
async getPublicPost(slug: string): Promise<PublicPostResponse>
```

**HTTP:** `GET /posts/:slug/public`

**Response:**

```json
{
  "slug": "my-post",
  "title": "My Post Title",
  "author": "John Doe",
  "html_content": "<h1>My Post</h1>...",
  "published_at": "2026-01-20T14:35:00+00:00"
}
```

**Errors:**

- 404: Post not found or not published

## Complete Workflows

### Workflow 1: Create → Edit → Save → Publish

Complete journey from creating a new post to publishing it.

#### Step 1: Create Draft

```tsx
import { useCreateDraft } from '@/hooks/usePosts'
import { useNavigate } from 'react-router-dom'
import { PostForm } from '@/components/post/PostForm'

function CreatePostPage() {
  const createDraft = useCreateDraft()
  const navigate = useNavigate()

  const handleSubmit = async (data: { slug: string; title: string }) => {
    try {
      const draft = await createDraft.mutateAsync(data)
      navigate(`/edit/${draft.slug}`)
    } catch (error) {
      console.error('Failed to create draft:', error)
    }
  }

  return (
    <div className="max-w-2xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Create New Post</h1>
      <PostForm onSubmit={handleSubmit} />
      {createDraft.error && (
        <p className="text-red-600 mt-4">{createDraft.error.message}</p>
      )}
    </div>
  )
}
```

#### Step 2: Edit and Save

```tsx
import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { useDraft, useSaveDraft } from '@/hooks/usePosts'
import { MarkdownEditor } from '@/components/post/MarkdownEditor'

function PostEditorPage() {
  const { slug } = useParams<{ slug: string }>()
  const { data: draft, isLoading } = useDraft(slug!)
  const saveDraft = useSaveDraft()
  const [content, setContent] = useState('')
  const [saveSuccess, setSaveSuccess] = useState(false)

  useEffect(() => {
    if (draft?.content) {
      setContent(draft.content)
    }
  }, [draft])

  const handleSave = async () => {
    try {
      await saveDraft.mutateAsync({ slug: slug!, content })
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 3000)
    } catch (error) {
      console.error('Failed to save:', error)
    }
  }

  if (isLoading) return <p>Loading draft...</p>

  return (
    <div className="max-w-7xl mx-auto p-6">
      <div className="mb-4 flex justify-between items-center">
        <h1 className="text-3xl font-bold">{draft?.title}</h1>
        <button
          onClick={handleSave}
          disabled={saveDraft.isPending}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          {saveDraft.isPending ? 'Saving...' : 'Save'}
        </button>
      </div>

      {saveSuccess && (
        <div className="mb-4 p-3 bg-green-100 text-green-800 rounded">
          Draft saved successfully!
        </div>
      )}

      <MarkdownEditor
        value={content}
        onChange={setContent}
        onSave={handleSave}
      />
    </div>
  )
}
```

#### Step 3: Publish

```tsx
import { useState } from 'react'
import { usePublishPost } from '@/hooks/usePosts'
import { useNavigate } from 'react-router-dom'

function PublishSection({ slug }: { slug: string }) {
  const publishPost = usePublishPost()
  const navigate = useNavigate()
  const [showConfirm, setShowConfirm] = useState(false)

  const handlePublish = async () => {
    try {
      await publishPost.mutateAsync(slug)
      navigate(`/posts/${slug}`)
    } catch (error) {
      console.error('Failed to publish:', error)
      setShowConfirm(false)
    }
  }

  return (
    <>
      <button
        onClick={() => setShowConfirm(true)}
        disabled={publishPost.isPending}
        className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
      >
        {publishPost.isPending ? 'Publishing...' : 'Publish'}
      </button>

      {showConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-white p-6 rounded shadow-lg max-w-md">
            <h2 className="text-xl font-bold mb-4">Publish Post</h2>
            <p className="mb-6">
              Are you sure you want to publish this post? It will be visible to all readers.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowConfirm(false)}
                className="px-4 py-2 border rounded hover:bg-gray-100"
              >
                Cancel
              </button>
              <button
                onClick={handlePublish}
                className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
              >
                Publish
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
```

### Workflow 2: List Posts with Filters and Pagination

Complete post list management interface.

```tsx
import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMyPosts, useDeleteDraft } from '@/hooks/usePosts'
import type { PostFilter } from '@/services/postsApi'

function MyPostsPage() {
  const navigate = useNavigate()
  const [filter, setFilter] = useState<PostFilter>('all')
  const [page, setPage] = useState(1)
  const [deleteSlug, setDeleteSlug] = useState<string | null>(null)

  const { data, isLoading, error } = useMyPosts(filter, page, 20)
  const deleteDraft = useDeleteDraft()

  const handleFilterChange = useCallback((newFilter: PostFilter) => {
    setFilter(newFilter)
    setPage(1)
  }, [])

  const handleDeleteConfirm = async () => {
    if (!deleteSlug) return
    try {
      await deleteDraft.mutateAsync(deleteSlug)
      setDeleteSlug(null)
    } catch (error) {
      console.error('Failed to delete:', error)
    }
  }

  if (isLoading) return <p>Loading posts...</p>
  if (error) return <p>Error loading posts</p>

  return (
    <div className="max-w-7xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">My Posts</h1>

      {/* Filter Tabs */}
      <div className="mb-6 flex gap-2">
        {(['all', 'drafts', 'published'] as const).map(f => (
          <button
            key={f}
            onClick={() => handleFilterChange(f)}
            className={`px-4 py-2 rounded ${
              filter === f
                ? 'bg-blue-600 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      {/* Posts Table */}
      {data && data.posts.length > 0 ? (
        <>
          <table className="min-w-full border rounded-lg overflow-hidden">
            <thead className="bg-gray-100">
              <tr>
                <th className="px-6 py-3 text-left">Title</th>
                <th className="px-6 py-3 text-left">Status</th>
                <th className="px-6 py-3 text-left">Last Updated</th>
                <th className="px-6 py-3 text-left">Actions</th>
              </tr>
            </thead>
            <tbody>
              {data.posts.map(post => (
                <tr key={post.slug} className="border-t hover:bg-gray-50">
                  <td className="px-6 py-4">{post.title}</td>
                  <td className="px-6 py-4">
                    <span
                      className={`px-2 py-1 rounded text-xs ${
                        post.published
                          ? 'bg-green-100 text-green-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {post.published ? 'Published' : 'Draft'}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    {new Date(post.updated_at).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex gap-2">
                      <button
                        onClick={() => navigate(`/edit/${post.slug}`)}
                        className="px-3 py-1 border rounded hover:bg-gray-100"
                      >
                        Edit
                      </button>
                      {post.published && (
                        <button
                          onClick={() => navigate(`/posts/${post.slug}`)}
                          className="px-3 py-1 border rounded hover:bg-gray-100"
                        >
                          View
                        </button>
                      )}
                      <button
                        onClick={() => setDeleteSlug(post.slug)}
                        className="px-3 py-1 border border-red-300 text-red-600 rounded hover:bg-red-50"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Pagination */}
          {data.total_pages > 1 && (
            <div className="mt-6 flex justify-between items-center">
              <p>Page {data.page} of {data.total_pages}</p>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage(p => p - 1)}
                  disabled={page <= 1}
                  className="px-4 py-2 border rounded disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Previous
                </button>
                <button
                  onClick={() => setPage(p => p + 1)}
                  disabled={page >= data.total_pages}
                  className="px-4 py-2 border rounded disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="text-center py-12 border rounded">
          <p className="text-gray-600">No posts found</p>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      {deleteSlug && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-white p-6 rounded shadow-lg max-w-md">
            <h2 className="text-xl font-bold mb-4">Delete Post</h2>
            <p className="mb-6">
              Are you sure you want to delete this post? This action cannot be undone.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setDeleteSlug(null)}
                className="px-4 py-2 border rounded hover:bg-gray-100"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteConfirm}
                disabled={deleteDraft.isPending}
                className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
              >
                {deleteDraft.isPending ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
```

### Workflow 3: Delete with Confirmation

Safe deletion pattern with confirmation dialog.

```tsx
import { useState } from 'react'
import { useDeleteDraft } from '@/hooks/usePosts'
import { useNavigate } from 'react-router-dom'

function DeleteDraftButton({ slug }: { slug: string }) {
  const [showConfirm, setShowConfirm] = useState(false)
  const deleteDraft = useDeleteDraft()
  const navigate = useNavigate()

  const handleDelete = async () => {
    try {
      await deleteDraft.mutateAsync(slug)
      navigate('/my-posts')
    } catch (error) {
      console.error('Failed to delete draft:', error)
      setShowConfirm(false)
    }
  }

  return (
    <>
      <button
        onClick={() => setShowConfirm(true)}
        className="px-4 py-2 border border-red-300 text-red-600 rounded hover:bg-red-50"
      >
        Delete Draft
      </button>

      {showConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg shadow-lg max-w-md">
            <h2 className="text-xl font-bold mb-4">Delete Draft</h2>
            <p className="mb-6 text-gray-700">
              Are you sure you want to delete this draft? This action cannot be undone.
              The post will be removed from the filesystem, database, and GitHub.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowConfirm(false)}
                disabled={deleteDraft.isPending}
                className="px-4 py-2 border rounded hover:bg-gray-100"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={deleteDraft.isPending}
                className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
              >
                {deleteDraft.isPending ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
```

## Testing

### Unit Testing with Vitest

Test components, hooks, and API client in isolation.

**Run tests:**

```bash
cd frontend
npm test                  # Run once
npm run test:watch        # Watch mode
npm run test:ui           # Vitest UI
npm run test:coverage     # Coverage report
```

**Example component test:**

```tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { PostForm } from '@/components/post/PostForm'

describe('PostForm', () => {
  it('normalizes slug input to lowercase with hyphens', () => {
    const onSubmit = vi.fn()
    render(<PostForm onSubmit={onSubmit} />)

    const slugInput = screen.getByTestId('post-form-slug-input')
    fireEvent.change(slugInput, { target: { value: 'Hello World!!!' } })

    expect(slugInput).toHaveValue('hello-world')
  })

  it('disables submit button until form is valid', () => {
    const onSubmit = vi.fn()
    render(<PostForm onSubmit={onSubmit} />)

    const submitButton = screen.getByTestId('post-form-submit')
    expect(submitButton).toBeDisabled()

    fireEvent.change(screen.getByTestId('post-form-slug-input'), {
      target: { value: 'test-post' }
    })
    fireEvent.change(screen.getByTestId('post-form-title-input'), {
      target: { value: 'Test Post' }
    })

    expect(submitButton).not.toBeDisabled()
  })
})
```

**Example hook test:**

```tsx
import { renderHook, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useDraft } from '@/hooks/usePosts'
import { postsApi } from '@/services/postsApi'

vi.mock('@/services/postsApi')
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({ getToken: async () => 'mock-token' })
}))

describe('useDraft', () => {
  it('fetches draft by slug', async () => {
    const mockDraft = {
      id: 1,
      slug: 'test-post',
      title: 'Test Post',
      content: '# Test',
      published: false
    }

    vi.mocked(postsApi.getDraft).mockResolvedValue(mockDraft)

    const queryClient = new QueryClient()
    const wrapper = ({ children }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )

    const { result } = renderHook(() => useDraft('test-post'), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(mockDraft)
  })
})
```

### E2E Testing with Playwright

Test complete user workflows in a real browser.

**Run tests:**

```bash
cd frontend
npm run test:e2e          # Headless mode
npm run test:e2e:headed   # Headed mode (see browser)
```

**Example E2E test:**

```typescript
import { test, expect } from '@playwright/test'

test.describe('Post Editor', () => {
  test('creates, edits, and publishes a post', async ({ page }) => {
    // Login
    await page.goto('/login')
    await page.fill('[name="email"]', 'author@example.com')
    await page.fill('[name="password"]', 'password123')
    await page.click('button[type="submit"]')

    // Create draft
    await page.goto('/create-post')
    await page.fill('[data-testid="post-form-slug-input"]', 'test-post')
    await page.fill('[data-testid="post-form-title-input"]', 'Test Post')
    await page.click('[data-testid="post-form-submit"]')

    // Edit content
    await expect(page).toHaveURL('/edit/test-post')
    await page.fill('textarea', '# My First Post\n\nThis is the content.')
    await page.click('button:has-text("Save")')
    await expect(page.locator('text=Draft saved successfully')).toBeVisible()

    // Publish
    await page.click('button:has-text("Publish")')
    await page.click('button:has-text("Publish"):last-child') // Confirm
    await expect(page).toHaveURL('/posts/test-post')
    await expect(page.locator('h1')).toHaveText('Test Post')
  })
})
```

## Accessibility

### ARIA Attributes

All interactive components include proper ARIA attributes for screen readers:

**PostForm:**

- `aria-invalid` on inputs with validation errors
- `aria-describedby` linking error messages to inputs
- `role="alert"` on error messages

**PostEditor:**

- `aria-live="polite"` on loading states
- `aria-label` on action buttons describing function
- `tabIndex={-1}` on success alert for focus management

**MyPosts:**

- `aria-pressed` on filter buttons indicating active state
- `aria-label` on action buttons with post context
- `role="group"` and `aria-label` on filter button group
- `aria-live="polite"` on pagination status

### Keyboard Navigation

All components support full keyboard navigation:

**MarkdownEditor:**

- Ctrl+S / Cmd+S: Save draft
- Standard textarea navigation (Tab, Arrow keys, etc.)

**PostForm:**

- Tab: Navigate between fields
- Enter: Submit form (when valid)

**PostEditor:**

- Tab: Navigate between Save/Publish buttons
- Enter: Activate focused button
- Esc: Close publish confirmation dialog

**MyPosts:**

- Tab: Navigate through filter tabs, action buttons, pagination
- Enter/Space: Activate focused button
- Arrow keys: Navigate table rows

### Focus Management

- Save success alert auto-focuses for screen reader announcement
- Dialogs trap focus within modal when open
- Focus returns to trigger button when dialog closes

## Security

### XSS Prevention

Multiple layers of protection against cross-site scripting:

**Client-Side Sanitization:**

Both MarkdownEditor and PreviewPane use **rehype-sanitize** plugin to strip dangerous HTML from markdown previews:

```typescript
import rehypeSanitize from 'rehype-sanitize'

<MarkdownPreview
  source={markdown}
  rehypePlugins={[[rehypeSanitize]]}
/>
```

**Server-Side Sanitization:**

Published posts are sanitized server-side with Bleach during the publish workflow. HTML content in `PublicPost` is already safe.

**Prevented Attacks:**

- `<script>` tags removed
- `onclick`, `onerror`, and other event handlers stripped
- `javascript:` protocol removed from links
- `<iframe>`, `<object>`, `<embed>` tags removed

### Authentication Security

**JWT Token Storage:**

Tokens managed entirely by Clerk SDK. Never stored in localStorage or sessionStorage.

**Token Transmission:**

All authenticated requests include `Authorization: Bearer <token>` header. Token retrieved via `getToken()` at request time.

**Automatic Token Refresh:**

Clerk SDK automatically refreshes tokens before expiration. No manual refresh logic needed.

### Input Validation

**Client-Side Validation:**

- Slug: Normalized to lowercase, hyphens only, max 200 chars
- Title: Non-empty string
- Content: No size limit (enforced server-side)

**Server-Side Validation:**

All inputs validated server-side. Client-side validation is UX enhancement only, not security boundary.

### CORS Configuration

Frontend configured to only make requests to `VITE_API_BASE_URL`. Backend CORS policy restricts origins in production.

---

**Last Updated:** 2026-02-08
