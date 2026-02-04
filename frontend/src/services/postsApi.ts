import axios from "axios";

/**
 * Post response from backend API
 */
export interface PostResponse {
	id: number;
	slug: string;
	title: string;
	author_id: number;
	html_content: string;
	published: boolean;
	published_at: string | null;
	created_at: string;
	updated_at: string;
}

/**
 * Response when saving a draft
 */
export interface SaveDraftResponse {
	message: string;
	slug: string;
}

/**
 * Paginated list of posts response
 */
export interface ListPostsResponse {
	posts: PostResponse[];
	total_count: number;
	total_pages: number;
	page: number;
	limit: number;
}

/**
 * Filter type for listing posts
 */
export type PostFilter = "all" | "drafts" | "published";

/**
 * API client instance
 *
 * Attempts eager initialization. In test environment with auto-mocking,
 * the initial call may return undefined, so we use lazy initialization
 * as fallback via getApiClient().
 */
let apiClientInstance = axios.create({
	baseURL: import.meta.env.VITE_API_BASE_URL || "/api",
});

/**
 * Get API client instance, creating it lazily if eager init returned undefined
 */
const getApiClient = () => {
	if (!apiClientInstance) {
		apiClientInstance = axios.create({
			baseURL: import.meta.env.VITE_API_BASE_URL || "/api",
		});
	}
	return apiClientInstance;
};

/**
 * Posts API service object
 */
export const postsApi = {
	/**
	 * Create a new draft post
	 *
	 * @param slug - URL-safe slug for the post
	 * @param title - Post title
	 * @param token - JWT authentication token
	 * @returns Created post data
	 * @throws AxiosError on validation errors (400), auth failures (401), or slug conflicts (409)
	 */
	async createDraft(
		slug: string,
		title: string,
		token: string,
	): Promise<PostResponse> {
		const response = await getApiClient().post<PostResponse>(
			"/posts",
			{ slug, title },
			{
				headers: { Authorization: `Bearer ${token}` },
			},
		);
		return response.data;
	},

	/**
	 * Retrieve a draft post by slug
	 *
	 * @param slug - Post slug identifier
	 * @param token - JWT authentication token
	 * @returns Post data
	 * @throws AxiosError on not found (404) or forbidden access (403)
	 */
	async getDraft(slug: string, token: string): Promise<PostResponse> {
		const response = await getApiClient().get<PostResponse>(`/posts/${slug}`, {
			headers: { Authorization: `Bearer ${token}` },
		});
		return response.data;
	},

	/**
	 * Save markdown content to an existing draft
	 *
	 * @param slug - Post slug identifier
	 * @param content - Markdown content to save
	 * @param token - JWT authentication token
	 * @returns Updated post data
	 * @throws AxiosError on validation errors (422), not found (404), or forbidden (403)
	 */
	async saveDraft(
		slug: string,
		content: string,
		token: string,
	): Promise<PostResponse> {
		const response = await getApiClient().put<PostResponse>(
			`/posts/${slug}`,
			{ content },
			{
				headers: { Authorization: `Bearer ${token}` },
			},
		);
		return response.data;
	},

	/**
	 * Delete a draft post permanently
	 *
	 * @param slug - Post slug identifier
	 * @param token - JWT authentication token
	 * @throws AxiosError on not found (404) or forbidden access (403)
	 */
	async deleteDraft(slug: string, token: string): Promise<void> {
		await getApiClient().delete(`/posts/${slug}`, {
			headers: { Authorization: `Bearer ${token}` },
		});
	},

	/**
	 * Publish a draft post
	 *
	 * @param slug - Post slug identifier
	 * @param token - JWT authentication token
	 * @returns Published post data with published=true and published_at timestamp
	 * @throws AxiosError on not found (404) or already published (409)
	 */
	async publishPost(slug: string, token: string): Promise<PostResponse> {
		const response = await getApiClient().post<PostResponse>(
			`/posts/${slug}/publish`,
			{},
			{
				headers: { Authorization: `Bearer ${token}` },
			},
		);
		return response.data;
	},

	/**
	 * Unpublish a published post
	 *
	 * @param slug - Post slug identifier
	 * @param token - JWT authentication token
	 * @returns Unpublished post data with published=false and published_at=null
	 * @throws AxiosError on not found (404) or not published (409)
	 */
	async unpublishPost(slug: string, token: string): Promise<PostResponse> {
		const response = await getApiClient().post<PostResponse>(
			`/posts/${slug}/unpublish`,
			{},
			{
				headers: { Authorization: `Bearer ${token}` },
			},
		);
		return response.data;
	},

	/**
	 * List posts belonging to the authenticated user
	 *
	 * @param filter - Optional filter: 'all', 'drafts', or 'published'
	 * @param page - Page number (defaults to 1)
	 * @param limit - Results per page (defaults to 20)
	 * @param token - JWT authentication token
	 * @returns Paginated list of posts with metadata
	 * @throws AxiosError on unauthorized (401)
	 */
	async listMyPosts(
		filter?: PostFilter,
		page?: number,
		limit?: number,
		token?: string,
	): Promise<ListPostsResponse> {
		const params: Record<string, string | number> = {
			page: page ?? 1,
			limit: limit ?? 20,
		};

		if (filter) {
			params.filter = filter;
		}

		const response = await getApiClient().get<ListPostsResponse>("/my-posts", {
			params,
			headers: token ? { Authorization: `Bearer ${token}` } : undefined,
		});
		return response.data;
	},
};
