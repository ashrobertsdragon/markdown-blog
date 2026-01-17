import { useEffect, useState } from "react";
import { type HealthResponse, healthService } from "@/services/healthService";

/**
 * Home page component
 *
 * Displays the application health status by fetching data from the health check API.
 * Shows loading state during data fetch, success state with health status,
 * and error state if the fetch fails.
 *
 * @returns Home page with health status display
 */
export default function Home() {
	const [loading, setLoading] = useState<boolean>(true);
	const [healthData, setHealthData] = useState<HealthResponse | null>(null);
	const [error, setError] = useState<Error | null>(null);

	useEffect(() => {
		const fetchHealthStatus = async () => {
			try {
				const data = await healthService.checkHealth();
				setHealthData(data);
				setError(null);
			} catch (err) {
				setError(err instanceof Error ? err : new Error("Unknown error"));
				setHealthData(null);
			} finally {
				setLoading(false);
			}
		};

		fetchHealthStatus();
	}, []);

	if (loading) {
		return (
			<div className="flex min-h-screen flex-col items-center justify-center bg-gray-50">
				<div className="text-center">
					<p className="text-lg text-gray-600">Loading...</p>
				</div>
			</div>
		);
	}

	if (error) {
		return (
			<div className="flex min-h-screen flex-col items-center justify-center bg-gray-50">
				<div className="text-center">
					<p className="mb-4 text-4xl font-bold text-red-600">
						Error: Unable to load health status
					</p>
				</div>
			</div>
		);
	}

	return (
		<div className="flex min-h-screen flex-col items-center justify-center bg-gray-50">
			<div className="text-center">
				<h1 className="mb-4 text-4xl font-bold text-gray-800">Home</h1>
				<div className="rounded-lg bg-white p-6 shadow-md">
					<p className="mb-2 text-xl font-semibold text-gray-700">
						System Status
					</p>
					<p className="text-lg text-gray-600">
						Status:{" "}
						<span className="font-medium text-green-600">
							{healthData?.status}
						</span>
					</p>
				</div>
			</div>
		</div>
	);
}
