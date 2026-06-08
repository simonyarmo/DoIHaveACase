import { Navigate, Route, Routes } from "react-router-dom"

import { AppLayout } from "@/components/AppLayout"
import { ProtectedRoute } from "@/components/ProtectedRoute"
import { Login } from "@/pages/auth/Login"
import { Signup } from "@/pages/auth/Signup"
import { Dashboard } from "@/pages/Dashboard"
import { CaseIntake } from "@/pages/CaseIntake"
import { CaseTimeline } from "@/pages/CaseTimeline"
import { CaseAssessment } from "@/pages/CaseAssessment"
import { DocumentStudio } from "@/pages/DocumentStudio"
import { NotificationSettings } from "@/pages/NotificationSettings"

function App() {
  return (
    <Routes>
      <Route path="/auth/login" element={<Login />} />
      <Route path="/auth/signup" element={<Signup />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/cases/new" element={<CaseIntake />} />
          <Route path="/cases/new/step/:n" element={<CaseIntake />} />
          <Route path="/cases/:id" element={<CaseTimeline />} />
          <Route path="/cases/:id/assessment" element={<CaseAssessment />} />
          <Route path="/cases/:id/documents" element={<DocumentStudio />} />
          <Route path="/settings/notifications" element={<NotificationSettings />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}

export default App
