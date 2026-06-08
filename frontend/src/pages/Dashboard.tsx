import { LayoutDashboard } from "lucide-react"

import { PlaceholderScreen } from "@/components/PlaceholderScreen"

export function Dashboard() {
  return (
    <PlaceholderScreen
      icon={LayoutDashboard}
      title="Dashboard"
      description="Your cases, deadline alerts, and expense totals will live here once intake and assessment agents are wired up."
    />
  )
}
