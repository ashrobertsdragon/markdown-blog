import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";

export default function NotFound() {
	return (
		<div className="flex min-h-screen flex-col items-center justify-center bg-gray-50">
			<div className="text-center">
				<h1 className="mb-4 text-9xl font-bold text-gray-800">404</h1>
				<h2 className="mb-8 text-4xl font-semibold text-gray-700">
					Page Not Found
				</h2>
				<p className="mb-8 text-lg text-gray-600">
					The page you're looking for doesn't exist or has been moved.
				</p>
				<Button asChild>
					<Link to="/">Go Home</Link>
				</Button>
			</div>
		</div>
	);
}
