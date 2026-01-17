import { useEffect, useState } from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
			<div className="flex min-h-screen flex-col items-center justify-center bg-gray-50 px-4">
				<Alert variant="destructive" className="max-w-md">
					<AlertTitle>Connection Error</AlertTitle>
					<AlertDescription>
						Error: Unable to load health status. Please try again later.
					</AlertDescription>
				</Alert>
			</div>
		);
	}

	return (
		<div className="flex min-h-screen flex-col items-center justify-center bg-gray-50 px-4">
			<div className="text-center">
				<h1 className="mb-4 text-4xl font-bold text-gray-800">Home</h1>
				<Card className="max-w-md">
					<CardHeader>
						<CardTitle>System Status</CardTitle>
					</CardHeader>
					<CardContent>
						<p className="text-lg text-gray-600">
							Status:{" "}
							<span className="font-medium text-green-600">
								{healthData?.status}
							</span>
						</p>
					</CardContent>
				</Card>
			</div>
		</div>
	);
}
