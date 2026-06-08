import { FilePlus2 } from "lucide-react"

import { PlaceholderScreen } from "@/components/PlaceholderScreen"

export function CaseIntake() {
  return (
    <PlaceholderScreen
      icon={FilePlus2}
      title="New case intake"
      description="The conversational intake agent will walk you through your case details here, step by step."
    />
  )
}
