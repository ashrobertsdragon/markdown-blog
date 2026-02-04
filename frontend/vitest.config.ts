import { defineConfig, mergeConfig } from "vitest/config";
import viteConfig from "./vite.config";

export default mergeConfig(
	viteConfig,
	defineConfig({
		test: {
			globals: true,
			environment: "jsdom",
			setupFiles: "./tests/setup.ts",
			include: [
				"tests/unit/**/*.test.{ts,tsx}",
				"tests/integration/**/*.test.{ts,tsx}",
			],
			exclude: ["tests/e2e/**/*"],
			env: {
				VITE_CLERK_PUBLISHABLE_KEY: "pk_test_test-key-for-vitest-testing",
			},
			coverage: {
				provider: "v8",
				reporter: ["text", "json", "html"],
				exclude: ["node_modules/", "tests/"],
			},
		},
	}),
);
