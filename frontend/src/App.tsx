import { BrowserRouter, Route, Routes } from "react-router-dom";
import Home from "@/pages/Home";
import NotFound from "@/pages/NotFound";

/**
 * Root application component with client-side routing
 *
 * Provides the main routing structure for the blog platform application.
 * Uses React Router's BrowserRouter for client-side navigation without hash symbols.
 * Configured for deployment at root domain (no basename).
 *
 * Routes:
 * - "/" - Home page displaying system health status
 * - "*" - 404 Not Found page for unmatched routes
 *
 * @returns Root application component with routing configuration
 */
export default function App() {
	return (
		<BrowserRouter>
			<Routes>
				<Route path="/" element={<Home />} />
				<Route path="*" element={<NotFound />} />
			</Routes>
		</BrowserRouter>
	);
}
