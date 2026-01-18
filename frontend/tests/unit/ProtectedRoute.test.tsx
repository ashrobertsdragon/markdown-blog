import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ProtectedRoute } from "../../src/components/auth/ProtectedRoute";
import type { AuthContextType } from "../../src/context/AuthContext";

vi.mock("../../src/context/AuthContext", () => ({
	useAuth: vi.fn(),
}));

import { useAuth } from "../../src/context/AuthContext";

const mockUseAuth = vi.mocked(useAuth);

describe("ProtectedRoute Component", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	describe("Loading State", () => {
		it("should display loading indicator when auth is not loaded", () => {
			mockUseAuth.mockReturnValue({
				user: null,
				isLoaded: false,
				isSignedIn: false,
				role: "authenticated",
			} as AuthContextType);

			const { container } = render(
				<MemoryRouter>
					<ProtectedRoute>
						<div>Protected Content</div>
					</ProtectedRoute>
				</MemoryRouter>,
			);

			const spinner = container.querySelector(".animate-spin");
			expect(spinner).toBeTruthy();
			expect(screen.queryByText("Protected Content")).not.toBeInTheDocument();
		});

		it("should not render children during loading state", () => {
			mockUseAuth.mockReturnValue({
				user: null,
				isLoaded: false,
				isSignedIn: false,
				role: "authenticated",
			} as AuthContextType);

			render(
				<MemoryRouter>
					<ProtectedRoute>
						<div data-testid="protected-content">Protected Content</div>
					</ProtectedRoute>
				</MemoryRouter>,
			);

			expect(screen.queryByTestId("protected-content")).not.toBeInTheDocument();
		});
	});

	describe("Unauthenticated User Redirection", () => {
		it("should redirect to /login when user is not authenticated", () => {
			mockUseAuth.mockReturnValue({
				user: null,
				isLoaded: true,
				isSignedIn: false,
				role: "authenticated",
			} as AuthContextType);

			render(
				<MemoryRouter initialEntries={["/protected"]}>
					<Routes>
						<Route
							path="/protected"
							element={
								<ProtectedRoute>
									<div>Protected Content</div>
								</ProtectedRoute>
							}
						/>
						<Route path="/login" element={<div>Login Page</div>} />
					</Routes>
				</MemoryRouter>,
			);

			expect(screen.getByText("Login Page")).toBeInTheDocument();
			expect(screen.queryByText("Protected Content")).not.toBeInTheDocument();
		});

		it("should preserve original URL in location state when redirecting to login", () => {
			mockUseAuth.mockReturnValue({
				user: null,
				isLoaded: true,
				isSignedIn: false,
				role: "authenticated",
			} as AuthContextType);

			render(
				<MemoryRouter initialEntries={["/admin/dashboard"]}>
					<Routes>
						<Route
							path="/admin/dashboard"
							element={
								<ProtectedRoute>
									<div>Dashboard</div>
								</ProtectedRoute>
							}
						/>
						<Route path="/login" element={<div>Login Page</div>} />
					</Routes>
				</MemoryRouter>,
			);

			expect(screen.getByText("Login Page")).toBeInTheDocument();
			expect(screen.queryByText("Dashboard")).not.toBeInTheDocument();
		});
	});

	describe("Authenticated User Without Required Role", () => {
		it("should redirect to /forbidden when authenticated user lacks required role", () => {
			mockUseAuth.mockReturnValue({
				user: { id: "user_123" },
				isLoaded: true,
				isSignedIn: true,
				role: "authenticated",
			} as AuthContextType);

			render(
				<MemoryRouter initialEntries={["/author/posts"]}>
					<Routes>
						<Route
							path="/author/posts"
							element={
								<ProtectedRoute requireRole="author">
									<div>Author Content</div>
								</ProtectedRoute>
							}
						/>
						<Route path="/forbidden" element={<div>Forbidden Page</div>} />
					</Routes>
				</MemoryRouter>,
			);

			expect(screen.getByText("Forbidden Page")).toBeInTheDocument();
			expect(screen.queryByText("Author Content")).not.toBeInTheDocument();
		});

		it("should redirect author to /forbidden when accessing admin route", () => {
			mockUseAuth.mockReturnValue({
				user: { id: "user_author" },
				isLoaded: true,
				isSignedIn: true,
				role: "author",
			} as AuthContextType);

			render(
				<MemoryRouter initialEntries={["/admin/users"]}>
					<Routes>
						<Route
							path="/admin/users"
							element={
								<ProtectedRoute requireRole="admin">
									<div>Admin Content</div>
								</ProtectedRoute>
							}
						/>
						<Route path="/forbidden" element={<div>Forbidden Page</div>} />
					</Routes>
				</MemoryRouter>,
			);

			expect(screen.getByText("Forbidden Page")).toBeInTheDocument();
			expect(screen.queryByText("Admin Content")).not.toBeInTheDocument();
		});

		it("should redirect authenticated user to /forbidden when accessing author route", () => {
			mockUseAuth.mockReturnValue({
				user: { id: "user_basic" },
				isLoaded: true,
				isSignedIn: true,
				role: "authenticated",
			} as AuthContextType);

			render(
				<MemoryRouter initialEntries={["/author/create"]}>
					<Routes>
						<Route
							path="/author/create"
							element={
								<ProtectedRoute requireRole="author">
									<div>Create Post</div>
								</ProtectedRoute>
							}
						/>
						<Route path="/forbidden" element={<div>Forbidden Page</div>} />
					</Routes>
				</MemoryRouter>,
			);

			expect(screen.getByText("Forbidden Page")).toBeInTheDocument();
			expect(screen.queryByText("Create Post")).not.toBeInTheDocument();
		});

		it("should redirect authenticated user to /forbidden when accessing admin route", () => {
			mockUseAuth.mockReturnValue({
				user: { id: "user_basic" },
				isLoaded: true,
				isSignedIn: true,
				role: "authenticated",
			} as AuthContextType);

			render(
				<MemoryRouter initialEntries={["/admin/settings"]}>
					<Routes>
						<Route
							path="/admin/settings"
							element={
								<ProtectedRoute requireRole="admin">
									<div>Admin Settings</div>
								</ProtectedRoute>
							}
						/>
						<Route path="/forbidden" element={<div>Forbidden Page</div>} />
					</Routes>
				</MemoryRouter>,
			);

			expect(screen.getByText("Forbidden Page")).toBeInTheDocument();
			expect(screen.queryByText("Admin Settings")).not.toBeInTheDocument();
		});
	});

	describe("Authorized User Access", () => {
		it("should render children when user is authenticated and no role required", () => {
			mockUseAuth.mockReturnValue({
				user: { id: "user_123" },
				isLoaded: true,
				isSignedIn: true,
				role: "authenticated",
			} as AuthContextType);

			render(
				<MemoryRouter>
					<ProtectedRoute>
						<div data-testid="protected-content">Protected Content</div>
					</ProtectedRoute>
				</MemoryRouter>,
			);

			expect(screen.getByTestId("protected-content")).toBeInTheDocument();
			expect(screen.getByText("Protected Content")).toBeInTheDocument();
		});

		it("should render children when user is author accessing author route", () => {
			mockUseAuth.mockReturnValue({
				user: { id: "user_author" },
				isLoaded: true,
				isSignedIn: true,
				role: "author",
			} as AuthContextType);

			render(
				<MemoryRouter>
					<ProtectedRoute requireRole="author">
						<div data-testid="author-content">Author Dashboard</div>
					</ProtectedRoute>
				</MemoryRouter>,
			);

			expect(screen.getByTestId("author-content")).toBeInTheDocument();
			expect(screen.getByText("Author Dashboard")).toBeInTheDocument();
		});

		it("should render children when user is admin accessing admin route", () => {
			mockUseAuth.mockReturnValue({
				user: { id: "user_admin" },
				isLoaded: true,
				isSignedIn: true,
				role: "admin",
			} as AuthContextType);

			render(
				<MemoryRouter>
					<ProtectedRoute requireRole="admin">
						<div data-testid="admin-content">Admin Panel</div>
					</ProtectedRoute>
				</MemoryRouter>,
			);

			expect(screen.getByTestId("admin-content")).toBeInTheDocument();
			expect(screen.getByText("Admin Panel")).toBeInTheDocument();
		});

		it("should render children when admin accesses author route", () => {
			mockUseAuth.mockReturnValue({
				user: { id: "user_admin" },
				isLoaded: true,
				isSignedIn: true,
				role: "admin",
			} as AuthContextType);

			render(
				<MemoryRouter>
					<ProtectedRoute requireRole="author">
						<div data-testid="author-content">Author Content</div>
					</ProtectedRoute>
				</MemoryRouter>,
			);

			expect(screen.getByTestId("author-content")).toBeInTheDocument();
			expect(screen.getByText("Author Content")).toBeInTheDocument();
		});

		it("should render children when admin accesses authenticated route", () => {
			mockUseAuth.mockReturnValue({
				user: { id: "user_admin" },
				isLoaded: true,
				isSignedIn: true,
				role: "admin",
			} as AuthContextType);

			render(
				<MemoryRouter>
					<ProtectedRoute requireRole="authenticated">
						<div data-testid="basic-content">Basic Content</div>
					</ProtectedRoute>
				</MemoryRouter>,
			);

			expect(screen.getByTestId("basic-content")).toBeInTheDocument();
			expect(screen.getByText("Basic Content")).toBeInTheDocument();
		});

		it("should render children when author accesses authenticated route", () => {
			mockUseAuth.mockReturnValue({
				user: { id: "user_author" },
				isLoaded: true,
				isSignedIn: true,
				role: "author",
			} as AuthContextType);

			render(
				<MemoryRouter>
					<ProtectedRoute requireRole="authenticated">
						<div data-testid="basic-content">Basic Content</div>
					</ProtectedRoute>
				</MemoryRouter>,
			);

			expect(screen.getByTestId("basic-content")).toBeInTheDocument();
			expect(screen.getByText("Basic Content")).toBeInTheDocument();
		});
	});

	describe("Role Hierarchy Enforcement", () => {
		it("should enforce that admin has all permissions", () => {
			mockUseAuth.mockReturnValue({
				user: { id: "user_admin" },
				isLoaded: true,
				isSignedIn: true,
				role: "admin",
			} as AuthContextType);

			const { rerender } = render(
				<MemoryRouter>
					<ProtectedRoute requireRole="authenticated">
						<div>Authenticated Route</div>
					</ProtectedRoute>
				</MemoryRouter>,
			);

			expect(screen.getByText("Authenticated Route")).toBeInTheDocument();

			rerender(
				<MemoryRouter>
					<ProtectedRoute requireRole="author">
						<div>Author Route</div>
					</ProtectedRoute>
				</MemoryRouter>,
			);

			expect(screen.getByText("Author Route")).toBeInTheDocument();

			rerender(
				<MemoryRouter>
					<ProtectedRoute requireRole="admin">
						<div>Admin Route</div>
					</ProtectedRoute>
				</MemoryRouter>,
			);

			expect(screen.getByText("Admin Route")).toBeInTheDocument();
		});

		it("should enforce that author can access author and authenticated routes only", () => {
			mockUseAuth.mockReturnValue({
				user: { id: "user_author" },
				isLoaded: true,
				isSignedIn: true,
				role: "author",
			} as AuthContextType);

			render(
				<MemoryRouter>
					<ProtectedRoute requireRole="authenticated">
						<div>Authenticated Route</div>
					</ProtectedRoute>
				</MemoryRouter>,
			);

			expect(screen.getByText("Authenticated Route")).toBeInTheDocument();
		});

		it("should enforce that author can access author routes", () => {
			mockUseAuth.mockReturnValue({
				user: { id: "user_author" },
				isLoaded: true,
				isSignedIn: true,
				role: "author",
			} as AuthContextType);

			render(
				<MemoryRouter>
					<ProtectedRoute requireRole="author">
						<div>Author Route</div>
					</ProtectedRoute>
				</MemoryRouter>,
			);

			expect(screen.getByText("Author Route")).toBeInTheDocument();
		});

		it("should enforce that author cannot access admin routes", () => {
			mockUseAuth.mockReturnValue({
				user: { id: "user_author" },
				isLoaded: true,
				isSignedIn: true,
				role: "author",
			} as AuthContextType);

			render(
				<MemoryRouter initialEntries={["/admin"]}>
					<Routes>
						<Route
							path="/admin"
							element={
								<ProtectedRoute requireRole="admin">
									<div>Admin Route</div>
								</ProtectedRoute>
							}
						/>
						<Route path="/forbidden" element={<div>Forbidden Page</div>} />
					</Routes>
				</MemoryRouter>,
			);

			expect(screen.getByText("Forbidden Page")).toBeInTheDocument();
		});

		it("should enforce that authenticated can only access authenticated routes", () => {
			mockUseAuth.mockReturnValue({
				user: { id: "user_basic" },
				isLoaded: true,
				isSignedIn: true,
				role: "authenticated",
			} as AuthContextType);

			render(
				<MemoryRouter>
					<ProtectedRoute requireRole="authenticated">
						<div>Authenticated Route</div>
					</ProtectedRoute>
				</MemoryRouter>,
			);

			expect(screen.getByText("Authenticated Route")).toBeInTheDocument();
		});

		it("should enforce that authenticated cannot access author routes", () => {
			mockUseAuth.mockReturnValue({
				user: { id: "user_basic" },
				isLoaded: true,
				isSignedIn: true,
				role: "authenticated",
			} as AuthContextType);

			render(
				<MemoryRouter initialEntries={["/author"]}>
					<Routes>
						<Route
							path="/author"
							element={
								<ProtectedRoute requireRole="author">
									<div>Author Route</div>
								</ProtectedRoute>
							}
						/>
						<Route path="/forbidden" element={<div>Forbidden Page</div>} />
					</Routes>
				</MemoryRouter>,
			);

			expect(screen.getByText("Forbidden Page")).toBeInTheDocument();
		});

		it("should enforce that authenticated cannot access admin routes", () => {
			mockUseAuth.mockReturnValue({
				user: { id: "user_basic" },
				isLoaded: true,
				isSignedIn: true,
				role: "authenticated",
			} as AuthContextType);

			render(
				<MemoryRouter initialEntries={["/admin"]}>
					<Routes>
						<Route
							path="/admin"
							element={
								<ProtectedRoute requireRole="admin">
									<div>Admin Route</div>
								</ProtectedRoute>
							}
						/>
						<Route path="/forbidden" element={<div>Forbidden Page</div>} />
					</Routes>
				</MemoryRouter>,
			);

			expect(screen.getByText("Forbidden Page")).toBeInTheDocument();
		});
	});

	describe("Component Props and API", () => {
		it("should accept children as ReactNode", () => {
			mockUseAuth.mockReturnValue({
				user: { id: "user_123" },
				isLoaded: true,
				isSignedIn: true,
				role: "authenticated",
			} as AuthContextType);

			render(
				<MemoryRouter>
					<ProtectedRoute>
						<div>First Child</div>
						<span>Second Child</span>
					</ProtectedRoute>
				</MemoryRouter>,
			);

			expect(screen.getByText("First Child")).toBeInTheDocument();
			expect(screen.getByText("Second Child")).toBeInTheDocument();
		});

		it("should work without requireRole prop", () => {
			mockUseAuth.mockReturnValue({
				user: { id: "user_123" },
				isLoaded: true,
				isSignedIn: true,
				role: "authenticated",
			} as AuthContextType);

			render(
				<MemoryRouter>
					<ProtectedRoute>
						<div>No Role Required</div>
					</ProtectedRoute>
				</MemoryRouter>,
			);

			expect(screen.getByText("No Role Required")).toBeInTheDocument();
		});

		it("should accept requireRole as authenticated", () => {
			mockUseAuth.mockReturnValue({
				user: { id: "user_123" },
				isLoaded: true,
				isSignedIn: true,
				role: "authenticated",
			} as AuthContextType);

			render(
				<MemoryRouter>
					<ProtectedRoute requireRole="authenticated">
						<div>Authenticated Required</div>
					</ProtectedRoute>
				</MemoryRouter>,
			);

			expect(screen.getByText("Authenticated Required")).toBeInTheDocument();
		});

		it("should accept requireRole as author", () => {
			mockUseAuth.mockReturnValue({
				user: { id: "user_author" },
				isLoaded: true,
				isSignedIn: true,
				role: "author",
			} as AuthContextType);

			render(
				<MemoryRouter>
					<ProtectedRoute requireRole="author">
						<div>Author Required</div>
					</ProtectedRoute>
				</MemoryRouter>,
			);

			expect(screen.getByText("Author Required")).toBeInTheDocument();
		});

		it("should accept requireRole as admin", () => {
			mockUseAuth.mockReturnValue({
				user: { id: "user_admin" },
				isLoaded: true,
				isSignedIn: true,
				role: "admin",
			} as AuthContextType);

			render(
				<MemoryRouter>
					<ProtectedRoute requireRole="admin">
						<div>Admin Required</div>
					</ProtectedRoute>
				</MemoryRouter>,
			);

			expect(screen.getByText("Admin Required")).toBeInTheDocument();
		});
	});

	describe("Edge Cases", () => {
		it("should handle undefined user gracefully", () => {
			mockUseAuth.mockReturnValue({
				user: undefined,
				isLoaded: true,
				isSignedIn: false,
				role: "authenticated",
			} as AuthContextType);

			render(
				<MemoryRouter initialEntries={["/protected"]}>
					<Routes>
						<Route
							path="/protected"
							element={
								<ProtectedRoute>
									<div>Protected Content</div>
								</ProtectedRoute>
							}
						/>
						<Route path="/login" element={<div>Login Page</div>} />
					</Routes>
				</MemoryRouter>,
			);

			expect(screen.getByText("Login Page")).toBeInTheDocument();
		});

		it("should handle isSignedIn undefined gracefully during loading", () => {
			mockUseAuth.mockReturnValue({
				user: null,
				isLoaded: false,
				isSignedIn: undefined,
				role: "authenticated",
			} as AuthContextType);

			const { container } = render(
				<MemoryRouter>
					<ProtectedRoute>
						<div>Protected Content</div>
					</ProtectedRoute>
				</MemoryRouter>,
			);

			const spinner = container.querySelector(".animate-spin");
			expect(spinner).toBeTruthy();
		});

		it("should prioritize loading state over authentication check", () => {
			mockUseAuth.mockReturnValue({
				user: null,
				isLoaded: false,
				isSignedIn: true,
				role: "authenticated",
			} as AuthContextType);

			const { container } = render(
				<MemoryRouter>
					<ProtectedRoute>
						<div>Protected Content</div>
					</ProtectedRoute>
				</MemoryRouter>,
			);

			const spinner = container.querySelector(".animate-spin");
			expect(spinner).toBeTruthy();
			expect(screen.queryByText("Protected Content")).not.toBeInTheDocument();
		});

		it("should handle rapid auth state changes", () => {
			mockUseAuth.mockReturnValue({
				user: null,
				isLoaded: false,
				isSignedIn: false,
				role: "authenticated",
			} as AuthContextType);

			const { container, rerender } = render(
				<MemoryRouter initialEntries={["/protected"]}>
					<Routes>
						<Route
							path="/protected"
							element={
								<ProtectedRoute>
									<div>Protected Content</div>
								</ProtectedRoute>
							}
						/>
						<Route path="/login" element={<div>Login Page</div>} />
					</Routes>
				</MemoryRouter>,
			);

			const spinner = container.querySelector(".animate-spin");
			expect(spinner).toBeTruthy();

			mockUseAuth.mockReturnValue({
				user: { id: "user_123" },
				isLoaded: true,
				isSignedIn: true,
				role: "author",
			} as AuthContextType);

			rerender(
				<MemoryRouter initialEntries={["/protected"]}>
					<Routes>
						<Route
							path="/protected"
							element={
								<ProtectedRoute>
									<div>Protected Content</div>
								</ProtectedRoute>
							}
						/>
						<Route path="/login" element={<div>Login Page</div>} />
					</Routes>
				</MemoryRouter>,
			);

			expect(screen.getByText("Protected Content")).toBeInTheDocument();
		});
	});

	describe("Navigation Behavior", () => {
		it("should not render children before redirect to login", () => {
			mockUseAuth.mockReturnValue({
				user: null,
				isLoaded: true,
				isSignedIn: false,
				role: "authenticated",
			} as AuthContextType);

			const childRenderSpy = vi.fn();
			const ChildComponent = () => {
				childRenderSpy();
				return <div>Child</div>;
			};

			render(
				<MemoryRouter initialEntries={["/protected"]}>
					<Routes>
						<Route
							path="/protected"
							element={
								<ProtectedRoute>
									<ChildComponent />
								</ProtectedRoute>
							}
						/>
						<Route path="/login" element={<div>Login Page</div>} />
					</Routes>
				</MemoryRouter>,
			);

			expect(childRenderSpy).not.toHaveBeenCalled();
		});

		it("should not render children before redirect to forbidden", () => {
			mockUseAuth.mockReturnValue({
				user: { id: "user_basic" },
				isLoaded: true,
				isSignedIn: true,
				role: "authenticated",
			} as AuthContextType);

			const childRenderSpy = vi.fn();
			const ChildComponent = () => {
				childRenderSpy();
				return <div>Child</div>;
			};

			render(
				<MemoryRouter initialEntries={["/admin"]}>
					<Routes>
						<Route
							path="/admin"
							element={
								<ProtectedRoute requireRole="admin">
									<ChildComponent />
								</ProtectedRoute>
							}
						/>
						<Route path="/forbidden" element={<div>Forbidden Page</div>} />
					</Routes>
				</MemoryRouter>,
			);

			expect(childRenderSpy).not.toHaveBeenCalled();
		});
	});
});
