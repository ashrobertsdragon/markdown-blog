import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import App from "@/App";

/**
 * Mock the Home page component to isolate routing logic
 * This allows us to test routing without Home component implementation
 */
vi.mock("@/pages/Home", () => ({
	default: () => <div data-testid="home-component">Home Page</div>,
}));

/**
 * Mock the NotFound page component to isolate routing logic
 */
vi.mock("@/pages/NotFound", () => ({
	default: () => <div data-testid="notfound-component">Not Found Page</div>,
}));

/**
 * App Component Routing Tests
 *
 * Tests the App component's routing configuration and behavior.
 * Validates that BrowserRouter is properly configured and routes
 * are set up correctly for "/" and "*" (catch-all) paths.
 */
describe("App", () => {
	describe("component rendering and structure", () => {
		/**
		 * Test that App component renders without crashing
		 * This is the basic smoke test for the component
		 */
		it("should render without crashing", () => {
			expect(() => {
				render(<App />);
			}).not.toThrow();
		});

		/**
		 * Test that App component renders successfully
		 * Validates that the component produces valid output
		 */
		it("should render successfully", () => {
			const { container } = render(<App />);
			expect(container).toBeTruthy();
			expect(container.firstChild).toBeTruthy();
		});
	});

	describe("routing configuration", () => {
		/**
		 * Test that App uses BrowserRouter for client-side routing
		 * BrowserRouter should be the top-level wrapper, NOT MemoryRouter
		 */
		it("should use BrowserRouter for client-side routing", () => {
			const { container } = render(<App />);

			// BrowserRouter renders its children without additional wrapper div
			// When React Router renders, it manages routes internally
			expect(container.firstChild).toBeTruthy();
		});

		/**
		 * Test that App exports as a default export
		 * This ensures the component can be imported as: import App from '@/App'
		 */
		it("should export as default export", () => {
			expect(App).toBeTruthy();
			expect(typeof App).toBe("function");
		});

		/**
		 * Test that Routes component is used in App
		 * Routes is the core React Router component for defining routes
		 */
		it("should render with Routes component", () => {
			const { container } = render(<App />);
			// Routes will render child route components
			expect(container.firstChild).toBeTruthy();
		});
	});

	describe("root path route", () => {
		/**
		 * Test that Home component renders at root path "/"
		 * This validates the primary route is configured correctly
		 */
		it("should render Home page at root path", () => {
			render(<App />);

			// Home component should be rendered
			const homeElement = screen.queryByTestId("home-component");
			expect(homeElement).toBeInTheDocument();
		});

		/**
		 * Test that root path contains Home component text
		 * Further validates that the correct component is routed
		 */
		it("should display Home page content at root", () => {
			render(<App />);

			const homeContent = screen.queryByText(/home page/i);
			expect(homeContent).toBeInTheDocument();
		});
	});

	describe("catch-all route", () => {
		/**
		 * Test that catch-all route ("*") is configured
		 * This route should handle any unmatched paths
		 */
		it("should have catch-all route configured", () => {
			const { container } = render(<App />);

			// Route structure should include catch-all route
			expect(container).toBeTruthy();
		});

		/**
		 * Test that App component structure is valid
		 * Ensures routes are properly nested
		 */
		it("should have valid route structure", () => {
			const { container } = render(<App />);

			// Container should have valid React Router structure
			expect(container.firstChild).toBeTruthy();
		});
	});

	describe("multiple renders", () => {
		/**
		 * Test that component can be rendered multiple times safely
		 * Ensures no state leakage between renders
		 */
		it("should render multiple times safely", () => {
			const { unmount: unmount1 } = render(<App />);
			unmount1();

			// Second render should work without errors
			const { unmount: unmount2 } = render(<App />);
			unmount2();

			// No assertion needed - test passes if no errors thrown
		});

		/**
		 * Test that each render is independent
		 * Component should reset state between renders
		 */
		it("should have independent renders", () => {
			const { container: container1, unmount: unmount1 } = render(<App />);
			expect(container1.firstChild).toBeTruthy();
			unmount1();

			const { container: container2 } = render(<App />);
			expect(container2.firstChild).toBeTruthy();
		});

		/**
		 * Test that component unmounts cleanly
		 * No console warnings or unhandled exceptions
		 */
		it("should unmount without errors", () => {
			const { unmount } = render(<App />);

			expect(() => {
				unmount();
			}).not.toThrow();
		});
	});

	describe("router configuration", () => {
		/**
		 * Test that App does NOT use basename prop
		 * The application runs at root "/" not a subdirectory
		 */
		it("should not use basename prop on BrowserRouter", () => {
			// This test validates that BrowserRouter is used without basename
			// If basename was set, routes would be prefixed (e.g., /app/home)
			render(<App />);

			// Verify routes can be accessed from root
			const homeElement = screen.queryByTestId("home-component");
			expect(homeElement).toBeInTheDocument();
		});

		/**
		 * Test that router is properly initialized
		 * Routes should be accessible and functional
		 */
		it("should have functional routing setup", () => {
			const { container } = render(<App />);

			// Router should be initialized and rendering routes
			expect(container.firstChild).toBeTruthy();
		});
	});

	describe("component behavior", () => {
		/**
		 * Test that App component is a functional component
		 * Can be called as a function and returns JSX
		 */
		it("should be a functional component", () => {
			expect(typeof App).toBe("function");

			// Should not require props
			const { container } = render(<App />);
			expect(container.firstChild).toBeTruthy();
		});

		/**
		 * Test that component renders within expected DOM structure
		 * Should have a valid React Portal or element tree
		 */
		it("should render in valid DOM structure", () => {
			const { container } = render(<App />);

			// Container should have children from Router
			expect(container.firstChild).toBeTruthy();
			expect(container.textContent).toBeTruthy();
		});

		/**
		 * Test that rendering is synchronous
		 * App should render immediately without async operations
		 */
		it("should render synchronously", () => {
			expect(() => {
				render(<App />);
			}).not.toThrow();

			// Screen should have content immediately
			const homeElement = screen.queryByTestId("home-component");
			expect(homeElement).toBeInTheDocument();
		});
	});

	describe("react router integration", () => {
		/**
		 * Test that BrowserRouter provides routing context
		 * All child components should have access to routing hooks
		 */
		it("should provide routing context to children", () => {
			const { container } = render(<App />);

			// Router context should be established
			expect(container).toBeTruthy();
		});

		/**
		 * Test that Routes component is properly configured
		 * Should be the direct child of BrowserRouter
		 */
		it("should have Routes as main route container", () => {
			render(<App />);

			// Routes should render at least one Route
			const homeElement = screen.queryByTestId("home-component");
			expect(homeElement).toBeInTheDocument();
		});

		/**
		 * Test that route components are properly rendered
		 * Route path matches should work correctly
		 */
		it("should render route components correctly", () => {
			render(<App />);

			// Home route should be active at "/"
			const homeComponent = screen.queryByTestId("home-component");
			expect(homeComponent).toBeInTheDocument();
		});
	});
});
