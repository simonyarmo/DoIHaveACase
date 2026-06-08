import { Navigate, Outlet, useLocation } from "react-router-dom"

import { useAuthStore } from "@/store/authStore"

export function ProtectedRoute() {
  const { session, loading } = useAuthStore()
  const location = useLocation()

  if (loading) {
    return <div className="flex h-screen items-center justify-center text-muted-foreground">Loading…</div>
  }

  if (!session) {
    return <Navigate to="/auth/login" state={{ from: location }} replace />
  }

  return <Outlet />
}
