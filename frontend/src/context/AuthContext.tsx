import { useAuth as useClerkAuth, useUser } from "@clerk/clerk-react";
import type { UserResource } from "@clerk/shared/types";
import type { ReactNode } from "react";
import { createContext, useContext } from "react";

export type UserType = UserResource;

export interface AuthContextType {
	user: UserType | null | undefined;
	isLoaded: boolean;
	isSignedIn: boolean | undefined;
	role: "authenticated" | "author" | "admin";
	getToken: (options?: { template?: string }) => Promise<string | null>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export interface AuthProviderProps {
	children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
	const { user, isLoaded, isSignedIn } = useUser();
	const { getToken } = useClerkAuth();

	const roleValue = user?.publicMetadata?.role;
	const role: AuthContextType["role"] =
		roleValue === "admin" ||
		roleValue === "author" ||
		roleValue === "authenticated"
			? roleValue
			: "authenticated";

	const value: AuthContextType = {
		user,
		isLoaded,
		isSignedIn,
		role,
		getToken,
	};

	return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextType {
	const context = useContext(AuthContext);
	if (!context) {
		throw new Error("useAuth must be used within AuthProvider");
	}
	return context;
}
