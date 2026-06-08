import { useParams } from "react-router-dom"
import { Clock } from "lucide-react"

import { PlaceholderScreen } from "@/components/PlaceholderScreen"

export function CaseTimeline() {
  const { id } = useParams<{ id: string }>()

  return (
    <PlaceholderScreen
      icon={Clock}
      title={`Case timeline${id ? ` — ${id}` : ""}`}
      description="Deadlines, milestones, and next steps for this case will appear here once the timeline engine is built."
    />
  )
}
