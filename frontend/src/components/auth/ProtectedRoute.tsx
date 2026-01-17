import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";

export interface ProtectedRouteProps {
	children: ReactNode;
	requireRole?: "authenticated" | "author" | "admin";
}

const canUserAccessRole = (
	userRole: "authenticated" | "author" | "admin",
	requiredRole: "authenticated" | "author" | "admin",
): boolean => {
	const roleHierarchy = {
		authenticated: 1,
		author: 2,
		admin: 3,
	};

	return roleHierarchy[userRole] >= roleHierarchy[requiredRole];
};

export function ProtectedRoute({ children, requireRole }: ProtectedRouteProps) {
	const { isLoaded, isSignedIn, role } = useAuth();
	const location = useLocation();

	if (!isLoaded) {
		return <div>Loading...</div>;
	}

	if (!isSignedIn) {
		return <Navigate to="/login" state={{ from: location }} replace />;
	}

	if (requireRole && !canUserAccessRole(role, requireRole)) {
		return <Navigate to="/forbidden" replace />;
	}

	return <>{children}</>;
}
