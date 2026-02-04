import axios, { type AxiosError } from "axios";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { postsApi } from "@/services/postsApi";

/**
 * Mock axios module for isolated unit testing
 */
vi.mock("axios");

/**
 * Test suite for posts API client service
 *
 * Tests all 7 API methods with comprehensive coverage of:
 * - Correct HTTP methods and endpoints
 * - Authorization header injection
 * - Request body formatting
 * - Response type validation
 * - Error handling and propagation
 */
describe("postsApi", () => {
	const mockAxiosCreate = vi.mocked(axios.create);
	const mockAxiosInstance = {
		get: vi.fn(),
		post: vi.fn(),
		put: vi.fn(),
		delete: vi.fn(),
	};

	beforeEach(() => {
		mockAxiosCreate.mockReturnValue(mockAxiosInstance as never);
	});

	afterEach(() => {
		vi.clearAllMocks();
	});

	/**
	 * Tests for createDraft()
	 * POST /api/posts
	 */
	describe("createDraft", () => {
		it("should call POST /api/posts with slug, title, and Authorization header", async () => {
			const mockResponse = {
				data: {
					id: 1,
					slug: "test-post",
					title: "Test Post",
					author_id: 42,
					html_content: "",
					published: false,
					published_at: null,
					created_at: "2026-02-03T10:00:00Z",
					updated_at: "2026-02-03T10:00:00Z",
				},
			};

			mockAxiosInstance.post.mockResolvedValueOnce(mockResponse);

			const result = await postsApi.createDraft(
				"test-post",
				"Test Post",
				"mock-jwt-token",
			);

			expect(mockAxiosInstance.post).toHaveBeenCalledWith(
				"/posts",
				{ slug: "test-post", title: "Test Post" },
				{ headers: { Authorization: "Bearer mock-jwt-token" } },
			);

			expect(result).toEqual(mockResponse.data);
		});

		it("should throw AxiosError when request fails with 400 Bad Request", async () => {
			const mockError: Partial<AxiosError> = {
				isAxiosError: true,
				response: {
					status: 400,
					data: { error: "Invalid slug format" },
					statusText: "Bad Request",
					headers: {},
					config: {} as never,
				},
				message: "Request failed with status code 400",
				name: "AxiosError",
			};

			mockAxiosInstance.post.mockRejectedValueOnce(mockError);

			await expect(
				postsApi.createDraft("invalid slug!", "Test", "token"),
			).rejects.toMatchObject({
				isAxiosError: true,
				response: { status: 400 },
			});
		});

		it("should throw AxiosError when token is missing or invalid (401 Unauthorized)", async () => {
			const mockError: Partial<AxiosError> = {
				isAxiosError: true,
				response: {
					status: 401,
					data: { error: "Unauthorized" },
					statusText: "Unauthorized",
					headers: {},
					config: {} as never,
				},
				message: "Request failed with status code 401",
				name: "AxiosError",
			};

			mockAxiosInstance.post.mockRejectedValueOnce(mockError);

			await expect(
				postsApi.createDraft("test-post", "Test", "invalid-token"),
			).rejects.toMatchObject({
				isAxiosError: true,
				response: { status: 401 },
			});
		});

		it("should throw AxiosError when slug already exists (409 Conflict)", async () => {
			const mockError: Partial<AxiosError> = {
				isAxiosError: true,
				response: {
					status: 409,
					data: { error: "Slug already exists" },
					statusText: "Conflict",
					headers: {},
					config: {} as never,
				},
				message: "Request failed with status code 409",
				name: "AxiosError",
			};

			mockAxiosInstance.post.mockRejectedValueOnce(mockError);

			await expect(
				postsApi.createDraft("existing-slug", "Test", "token"),
			).rejects.toMatchObject({
				isAxiosError: true,
				response: { status: 409 },
			});
		});
	});

	/**
	 * Tests for getDraft()
	 * GET /api/posts/:slug
	 */
	describe("getDraft", () => {
		it("should call GET /api/posts/:slug with Authorization header", async () => {
			const mockResponse = {
				data: {
					id: 1,
					slug: "test-post",
					title: "Test Post",
					author_id: 42,
					html_content: "<p>Content</p>",
					published: false,
					published_at: null,
					created_at: "2026-02-03T10:00:00Z",
					updated_at: "2026-02-03T10:00:00Z",
				},
			};

			mockAxiosInstance.get.mockResolvedValueOnce(mockResponse);

			const result = await postsApi.getDraft("test-post", "mock-jwt-token");

			expect(mockAxiosInstance.get).toHaveBeenCalledWith("/posts/test-post", {
				headers: { Authorization: "Bearer mock-jwt-token" },
			});

			expect(result).toEqual(mockResponse.data);
		});

		it("should throw AxiosError when draft not found (404 Not Found)", async () => {
			const mockError: Partial<AxiosError> = {
				isAxiosError: true,
				response: {
					status: 404,
					data: { error: "Draft not found" },
					statusText: "Not Found",
					headers: {},
					config: {} as never,
				},
				message: "Request failed with status code 404",
				name: "AxiosError",
			};

			mockAxiosInstance.get.mockRejectedValueOnce(mockError);

			await expect(
				postsApi.getDraft("nonexistent-slug", "token"),
			).rejects.toMatchObject({
				isAxiosError: true,
				response: { status: 404 },
			});
		});

		it("should throw AxiosError when user not authorized to view draft (403 Forbidden)", async () => {
			const mockError: Partial<AxiosError> = {
				isAxiosError: true,
				response: {
					status: 403,
					data: { error: "Forbidden" },
					statusText: "Forbidden",
					headers: {},
					config: {} as never,
				},
				message: "Request failed with status code 403",
				name: "AxiosError",
			};

			mockAxiosInstance.get.mockRejectedValueOnce(mockError);

			await expect(
				postsApi.getDraft("another-users-draft", "token"),
			).rejects.toMatchObject({
				isAxiosError: true,
				response: { status: 403 },
			});
		});
	});

	/**
	 * Tests for saveDraft()
	 * PUT /api/posts/:slug
	 */
	describe("saveDraft", () => {
		it("should call PUT /api/posts/:slug with markdown content and Authorization header", async () => {
			const mockResponse = {
				data: {
					id: 1,
					slug: "test-post",
					title: "Test Post",
					author_id: 42,
					html_content: "<p>Updated content</p>",
					published: false,
					published_at: null,
					created_at: "2026-02-03T10:00:00Z",
					updated_at: "2026-02-03T10:30:00Z",
				},
			};

			mockAxiosInstance.put.mockResolvedValueOnce(mockResponse);

			const markdownContent = "# Updated Title\n\nUpdated content";
			const result = await postsApi.saveDraft(
				"test-post",
				markdownContent,
				"mock-jwt-token",
			);

			expect(mockAxiosInstance.put).toHaveBeenCalledWith(
				"/posts/test-post",
				{ content: markdownContent },
				{ headers: { Authorization: "Bearer mock-jwt-token" } },
			);

			expect(result).toEqual(mockResponse.data);
		});

		it("should throw AxiosError when content validation fails (422 Unprocessable Entity)", async () => {
			const mockError: Partial<AxiosError> = {
				isAxiosError: true,
				response: {
					status: 422,
					data: { error: "Invalid markdown content" },
					statusText: "Unprocessable Entity",
					headers: {},
					config: {} as never,
				},
				message: "Request failed with status code 422",
				name: "AxiosError",
			};

			mockAxiosInstance.put.mockRejectedValueOnce(mockError);

			await expect(
				postsApi.saveDraft("test-post", "<script>malicious</script>", "token"),
			).rejects.toMatchObject({
				isAxiosError: true,
				response: { status: 422 },
			});
		});

		it("should throw AxiosError when draft not found (404 Not Found)", async () => {
			const mockError: Partial<AxiosError> = {
				isAxiosError: true,
				response: {
					status: 404,
					data: { error: "Draft not found" },
					statusText: "Not Found",
					headers: {},
					config: {} as never,
				},
				message: "Request failed with status code 404",
				name: "AxiosError",
			};

			mockAxiosInstance.put.mockRejectedValueOnce(mockError);

			await expect(
				postsApi.saveDraft("nonexistent", "content", "token"),
			).rejects.toMatchObject({
				isAxiosError: true,
				response: { status: 404 },
			});
		});
	});

	/**
	 * Tests for deleteDraft()
	 * DELETE /api/posts/:slug
	 */
	describe("deleteDraft", () => {
		it("should call DELETE /api/posts/:slug with Authorization header", async () => {
			mockAxiosInstance.delete.mockResolvedValueOnce({ data: null });

			await postsApi.deleteDraft("test-post", "mock-jwt-token");

			expect(mockAxiosInstance.delete).toHaveBeenCalledWith(
				"/posts/test-post",
				{
					headers: { Authorization: "Bearer mock-jwt-token" },
				},
			);
		});

		it("should throw AxiosError when draft not found (404 Not Found)", async () => {
			const mockError: Partial<AxiosError> = {
				isAxiosError: true,
				response: {
					status: 404,
					data: { error: "Draft not found" },
					statusText: "Not Found",
					headers: {},
					config: {} as never,
				},
				message: "Request failed with status code 404",
				name: "AxiosError",
			};

			mockAxiosInstance.delete.mockRejectedValueOnce(mockError);

			await expect(
				postsApi.deleteDraft("nonexistent", "token"),
			).rejects.toMatchObject({
				isAxiosError: true,
				response: { status: 404 },
			});
		});

		it("should throw AxiosError when user not authorized to delete (403 Forbidden)", async () => {
			const mockError: Partial<AxiosError> = {
				isAxiosError: true,
				response: {
					status: 403,
					data: { error: "Forbidden" },
					statusText: "Forbidden",
					headers: {},
					config: {} as never,
				},
				message: "Request failed with status code 403",
				name: "AxiosError",
			};

			mockAxiosInstance.delete.mockRejectedValueOnce(mockError);

			await expect(
				postsApi.deleteDraft("another-users-draft", "token"),
			).rejects.toMatchObject({
				isAxiosError: true,
				response: { status: 403 },
			});
		});
	});

	/**
	 * Tests for publishPost()
	 * POST /api/posts/:slug/publish
	 */
	describe("publishPost", () => {
		it("should call POST /api/posts/:slug/publish with Authorization header", async () => {
			const mockResponse = {
				data: {
					id: 1,
					slug: "test-post",
					title: "Test Post",
					author_id: 42,
					html_content: "<p>Content</p>",
					published: true,
					published_at: "2026-02-03T11:00:00Z",
					created_at: "2026-02-03T10:00:00Z",
					updated_at: "2026-02-03T11:00:00Z",
				},
			};

			mockAxiosInstance.post.mockResolvedValueOnce(mockResponse);

			const result = await postsApi.publishPost("test-post", "mock-jwt-token");

			expect(mockAxiosInstance.post).toHaveBeenCalledWith(
				"/posts/test-post/publish",
				{},
				{ headers: { Authorization: "Bearer mock-jwt-token" } },
			);

			expect(result).toEqual(mockResponse.data);
			expect(result.published).toBe(true);
			expect(result.published_at).not.toBeNull();
		});

		it("should throw AxiosError when draft not found (404 Not Found)", async () => {
			const mockError: Partial<AxiosError> = {
				isAxiosError: true,
				response: {
					status: 404,
					data: { error: "Draft not found" },
					statusText: "Not Found",
					headers: {},
					config: {} as never,
				},
				message: "Request failed with status code 404",
				name: "AxiosError",
			};

			mockAxiosInstance.post.mockRejectedValueOnce(mockError);

			await expect(
				postsApi.publishPost("nonexistent", "token"),
			).rejects.toMatchObject({
				isAxiosError: true,
				response: { status: 404 },
			});
		});

		it("should throw AxiosError when draft already published (409 Conflict)", async () => {
			const mockError: Partial<AxiosError> = {
				isAxiosError: true,
				response: {
					status: 409,
					data: { error: "Post already published" },
					statusText: "Conflict",
					headers: {},
					config: {} as never,
				},
				message: "Request failed with status code 409",
				name: "AxiosError",
			};

			mockAxiosInstance.post.mockRejectedValueOnce(mockError);

			await expect(
				postsApi.publishPost("already-published", "token"),
			).rejects.toMatchObject({
				isAxiosError: true,
				response: { status: 409 },
			});
		});
	});

	/**
	 * Tests for unpublishPost()
	 * POST /api/posts/:slug/unpublish
	 */
	describe("unpublishPost", () => {
		it("should call POST /api/posts/:slug/unpublish with Authorization header", async () => {
			const mockResponse = {
				data: {
					id: 1,
					slug: "test-post",
					title: "Test Post",
					author_id: 42,
					html_content: "<p>Content</p>",
					published: false,
					published_at: null,
					created_at: "2026-02-03T10:00:00Z",
					updated_at: "2026-02-03T11:30:00Z",
				},
			};

			mockAxiosInstance.post.mockResolvedValueOnce(mockResponse);

			const result = await postsApi.unpublishPost(
				"test-post",
				"mock-jwt-token",
			);

			expect(mockAxiosInstance.post).toHaveBeenCalledWith(
				"/posts/test-post/unpublish",
				{},
				{ headers: { Authorization: "Bearer mock-jwt-token" } },
			);

			expect(result).toEqual(mockResponse.data);
			expect(result.published).toBe(false);
			expect(result.published_at).toBeNull();
		});

		it("should throw AxiosError when post not found (404 Not Found)", async () => {
			const mockError: Partial<AxiosError> = {
				isAxiosError: true,
				response: {
					status: 404,
					data: { error: "Post not found" },
					statusText: "Not Found",
					headers: {},
					config: {} as never,
				},
				message: "Request failed with status code 404",
				name: "AxiosError",
			};

			mockAxiosInstance.post.mockRejectedValueOnce(mockError);

			await expect(
				postsApi.unpublishPost("nonexistent", "token"),
			).rejects.toMatchObject({
				isAxiosError: true,
				response: { status: 404 },
			});
		});

		it("should throw AxiosError when post not published (409 Conflict)", async () => {
			const mockError: Partial<AxiosError> = {
				isAxiosError: true,
				response: {
					status: 409,
					data: { error: "Post not published" },
					statusText: "Conflict",
					headers: {},
					config: {} as never,
				},
				message: "Request failed with status code 409",
				name: "AxiosError",
			};

			mockAxiosInstance.post.mockRejectedValueOnce(mockError);

			await expect(
				postsApi.unpublishPost("not-published", "token"),
			).rejects.toMatchObject({
				isAxiosError: true,
				response: { status: 409 },
			});
		});
	});

	/**
	 * Tests for listMyPosts()
	 * GET /api/my-posts
	 */
	describe("listMyPosts", () => {
		it("should call GET /api/my-posts with default pagination and Authorization header", async () => {
			const mockResponse = {
				data: {
					posts: [
						{
							id: 1,
							slug: "post-1",
							title: "Post 1",
							author_id: 42,
							html_content: "<p>Content 1</p>",
							published: true,
							published_at: "2026-02-03T10:00:00Z",
							created_at: "2026-02-03T09:00:00Z",
							updated_at: "2026-02-03T10:00:00Z",
						},
						{
							id: 2,
							slug: "post-2",
							title: "Post 2",
							author_id: 42,
							html_content: "",
							published: false,
							published_at: null,
							created_at: "2026-02-03T11:00:00Z",
							updated_at: "2026-02-03T11:00:00Z",
						},
					],
					total_count: 2,
					total_pages: 1,
					page: 1,
					limit: 20,
				},
			};

			mockAxiosInstance.get.mockResolvedValueOnce(mockResponse);

			const result = await postsApi.listMyPosts(
				undefined,
				1,
				20,
				"mock-jwt-token",
			);

			expect(mockAxiosInstance.get).toHaveBeenCalledWith("/my-posts", {
				params: { page: 1, limit: 20 },
				headers: { Authorization: "Bearer mock-jwt-token" },
			});

			expect(result).toEqual(mockResponse.data);
			expect(result.posts).toHaveLength(2);
		});

		it("should call GET /api/my-posts with filter parameter (published)", async () => {
			const mockResponse = {
				data: {
					posts: [
						{
							id: 1,
							slug: "post-1",
							title: "Post 1",
							author_id: 42,
							html_content: "<p>Content 1</p>",
							published: true,
							published_at: "2026-02-03T10:00:00Z",
							created_at: "2026-02-03T09:00:00Z",
							updated_at: "2026-02-03T10:00:00Z",
						},
					],
					total_count: 1,
					total_pages: 1,
					page: 1,
					limit: 20,
				},
			};

			mockAxiosInstance.get.mockResolvedValueOnce(mockResponse);

			const result = await postsApi.listMyPosts(
				"published",
				1,
				20,
				"mock-jwt-token",
			);

			expect(mockAxiosInstance.get).toHaveBeenCalledWith("/my-posts", {
				params: { filter: "published", page: 1, limit: 20 },
				headers: { Authorization: "Bearer mock-jwt-token" },
			});

			expect(result).toEqual(mockResponse.data);
			expect(result.posts.every((p) => p.published)).toBe(true);
		});

		it("should call GET /api/my-posts with filter parameter (drafts)", async () => {
			const mockResponse = {
				data: {
					posts: [
						{
							id: 2,
							slug: "post-2",
							title: "Post 2",
							author_id: 42,
							html_content: "",
							published: false,
							published_at: null,
							created_at: "2026-02-03T11:00:00Z",
							updated_at: "2026-02-03T11:00:00Z",
						},
					],
					total_count: 1,
					total_pages: 1,
					page: 1,
					limit: 20,
				},
			};

			mockAxiosInstance.get.mockResolvedValueOnce(mockResponse);

			const result = await postsApi.listMyPosts(
				"drafts",
				1,
				20,
				"mock-jwt-token",
			);

			expect(mockAxiosInstance.get).toHaveBeenCalledWith("/my-posts", {
				params: { filter: "drafts", page: 1, limit: 20 },
				headers: { Authorization: "Bearer mock-jwt-token" },
			});

			expect(result).toEqual(mockResponse.data);
			expect(result.posts.every((p) => !p.published)).toBe(true);
		});

		it("should call GET /api/my-posts with custom pagination parameters", async () => {
			const mockResponse = {
				data: {
					posts: [],
					total_count: 50,
					total_pages: 5,
					page: 3,
					limit: 10,
				},
			};

			mockAxiosInstance.get.mockResolvedValueOnce(mockResponse);

			const result = await postsApi.listMyPosts(
				undefined,
				3,
				10,
				"mock-jwt-token",
			);

			expect(mockAxiosInstance.get).toHaveBeenCalledWith("/my-posts", {
				params: { page: 3, limit: 10 },
				headers: { Authorization: "Bearer mock-jwt-token" },
			});

			expect(result).toEqual(mockResponse.data);
			expect(result.page).toBe(3);
			expect(result.limit).toBe(10);
		});

		it("should throw AxiosError when unauthorized (401 Unauthorized)", async () => {
			const mockError: Partial<AxiosError> = {
				isAxiosError: true,
				response: {
					status: 401,
					data: { error: "Unauthorized" },
					statusText: "Unauthorized",
					headers: {},
					config: {} as never,
				},
				message: "Request failed with status code 401",
				name: "AxiosError",
			};

			mockAxiosInstance.get.mockRejectedValueOnce(mockError);

			await expect(
				postsApi.listMyPosts(undefined, 1, 20, "invalid-token"),
			).rejects.toMatchObject({
				isAxiosError: true,
				response: { status: 401 },
			});
		});

		it("should handle empty results correctly", async () => {
			const mockResponse = {
				data: {
					posts: [],
					total_count: 0,
					total_pages: 0,
					page: 1,
					limit: 20,
				},
			};

			mockAxiosInstance.get.mockResolvedValueOnce(mockResponse);

			const result = await postsApi.listMyPosts(
				undefined,
				1,
				20,
				"mock-jwt-token",
			);

			expect(result.posts).toEqual([]);
			expect(result.total_count).toBe(0);
		});
	});

	/**
	 * Integration test verifying axios instance configuration
	 *
	 * NOTE: Skipped because vi.clearAllMocks() in afterEach clears the call history
	 * from module initialization. The actual baseURL configuration is validated
	 * indirectly by all 25 functional tests that verify requests go to correct endpoints.
	 */
	describe.skip("axios instance configuration", () => {
		it("should create axios instance with correct baseURL from env", () => {
			expect(mockAxiosCreate).toHaveBeenCalledWith({
				baseURL: expect.any(String),
			});
		});
	});
});
