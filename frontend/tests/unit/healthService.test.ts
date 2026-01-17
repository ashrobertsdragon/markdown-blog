import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("axios", () => import("../mocks/axios"));

import type {
	DatabaseHealthResponse,
	GitHubHealthResponse,
	HealthResponse,
} from "@/services/healthService";
import { healthService } from "@/services/healthService";
import { mockAxiosGet } from "../mocks/axios";

describe("healthService", () => {
	beforeEach(() => {
		mockAxiosGet.mockClear();
	});

	describe("checkHealth", () => {
		it("should call GET /health and return response data", async () => {
			const mockData: HealthResponse = { status: "healthy" };
			mockAxiosGet.mockResolvedValue({ data: mockData });

			const result = await healthService.checkHealth();

			expect(mockAxiosGet).toHaveBeenCalledWith("/health");
			expect(result).toEqual(mockData);
		});

		it("should propagate errors to caller", async () => {
			const mockError = new Error("Network error");
			mockAxiosGet.mockRejectedValue(mockError);

			await expect(healthService.checkHealth()).rejects.toThrow(
				"Network error",
			);
		});
	});

	describe("checkDatabase", () => {
		it("should call GET /health/db and return response data", async () => {
			const mockData: DatabaseHealthResponse = {
				status: "healthy",
				database: "connected",
			};
			mockAxiosGet.mockResolvedValue({ data: mockData });

			const result = await healthService.checkDatabase();

			expect(mockAxiosGet).toHaveBeenCalledWith("/health/db");
			expect(result).toEqual(mockData);
		});

		it("should propagate errors to caller", async () => {
			const mockError = new Error("Database connection failed");
			mockAxiosGet.mockRejectedValue(mockError);

			await expect(healthService.checkDatabase()).rejects.toThrow(
				"Database connection failed",
			);
		});
	});

	describe("checkGitHub", () => {
		it("should call GET /health/github and return response data", async () => {
			const mockData: GitHubHealthResponse = {
				status: "healthy",
				github: "reachable",
			};
			mockAxiosGet.mockResolvedValue({ data: mockData });

			const result = await healthService.checkGitHub();

			expect(mockAxiosGet).toHaveBeenCalledWith("/health/github");
			expect(result).toEqual(mockData);
		});

		it("should propagate errors to caller", async () => {
			const mockError = new Error("GitHub API unreachable");
			mockAxiosGet.mockRejectedValue(mockError);

			await expect(healthService.checkGitHub()).rejects.toThrow(
				"GitHub API unreachable",
			);
		});
	});
});
