# Image Upload

Authors can upload images directly from the PostEditor and embed them in draft posts. Images are stored on the filesystem and served by Flask with long-lived cache headers.

---

## Configuration

| Environment Variable | Default                     | Description                                 |
| -------------------- | --------------------------- | ------------------------------------------- |
| `UPLOADS_PATH`       | `{project_root}/../uploads` | Absolute path to the image upload directory |
| `MAX_UPLOAD_SIZE`    | `5242880` (5 MB)            | Maximum accepted file size in bytes         |

Set these in your `.env` file or deployment environment. The directory at `UPLOADS_PATH` is created automatically on first use.

---

## API Reference

All endpoints require a valid Clerk JWT in the `Authorization: Bearer <token>` header unless noted.

### POST /api/posts/{slug}/images

Upload an image to a draft.

**Auth:** Required. Must be the post author or an admin.

**Request:** `multipart/form-data` with field `file` containing the image.

**Supported types:** JPEG, PNG, GIF, WebP (validated via magic bytes + extension).

**Size limit:** Controlled by `MAX_UPLOAD_SIZE`.

**Response 201:**

```json
{ "url": "/uploads/{slug}/{sanitized-filename}" }
```

**Error responses:**

| Status | Condition                                 |
| ------ | ----------------------------------------- |
| 400    | Unsupported file type or invalid filename |
| 401    | Missing or invalid token                  |
| 403    | Authenticated but not the post owner      |
| 413    | File exceeds `MAX_UPLOAD_SIZE`            |

---

### GET /api/posts/{slug}/images

List all images uploaded to a draft.

**Auth:** Required. Must be the post author or an admin.

**Response 200:**

```json
{ "images": ["/uploads/{slug}/{filename}", ...] }
```

Returns `{"images": []}` if no images have been uploaded.

---

### DELETE /api/posts/{slug}/images/{filename}

Delete an uploaded image.

**Auth:** Required. Must be the post author or an admin.

**Response 204:** No content on success.

**Error responses:**

| Status | Condition                |
| ------ | ------------------------ |
| 401    | Missing or invalid token |
| 403    | Not the post owner       |
| 404    | File not found           |

---

### GET /uploads/{slug}/{filename}

Serve an uploaded image file. No authentication required (images in published posts are public).

**Response 200:** Image bytes with correct `Content-Type` and `Cache-Control: public, max-age=31536000`.

**Response 403:** Returned if the resolved path escapes `UPLOADS_PATH` (path traversal attempt).

---

## Filesystem Layout

```text
uploads/               ← UPLOADS_PATH root
└── {slug}/            ← created on first upload for that post
    ├── photo.jpg
    ├── diagram.png
    └── ...
```

The directory structure mirrors the post slug. Flask's `send_from_directory` serves files directly from `UPLOADS_PATH`.

---

## Frontend Integration

`ImageUploadButton` (in `src/components/admin/ImageUploadButton.tsx`) is rendered in the `PostEditor` toolbar when editing an existing draft. It:

1. Shows a hidden `<input type="file" accept="image/*">` triggered by button click or drag-and-drop.
1. Uploads the file via `imagesApi.uploadImage` (in `src/services/imagesApi.ts`).
1. On success, calls `onInsert("![{filename}]({url})")` which inserts the markdown at the last cursor position tracked in `PostEditor`.
1. Shows a success toast on upload, an error toast on failure.
1. Disables the button and shows a spinner while uploading.

Cursor position is tracked via `onSelect`/`onClick`/`onKeyUp` events forwarded through `MarkdownEditor`'s `textareaProps` prop.

---

## Security Model

| Control                   | Implementation                                                                                                 |
| ------------------------- | -------------------------------------------------------------------------------------------------------------- |
| Magic bytes validation    | First 12 bytes checked against known PNG/JPEG/GIF/WebP signatures                                              |
| Extension allowlist       | `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp` only                                                                  |
| Filename sanitization     | `ImageFilename` value object: stem restricted to `[a-zA-Z0-9_-]`, max 100 chars, single extension              |
| Path traversal prevention | `serve_upload` resolves the path and checks it starts with `UPLOADS_PATH` before calling `send_from_directory` |
| Ownership check           | Upload, list, and delete endpoints verify `post.author_id == current_user.id` or `role == "admin"`             |
| No executable types       | Extension allowlist excludes `.php`, `.py`, `.sh`, and all non-image types                                     |
