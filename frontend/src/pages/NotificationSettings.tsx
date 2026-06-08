import { Settings } from "lucide-react"

import { PlaceholderScreen } from "@/components/PlaceholderScreen"

export function NotificationSettings() {
  return (
    <PlaceholderScreen
      icon={Settings}
      title="Notification settings"
      description="Manage SMS and deadline alert preferences here once the alerts system is wired up."
    />
  )
}
