import { useParams } from "react-router-dom"
import { ScanSearch } from "lucide-react"

import { PlaceholderScreen } from "@/components/PlaceholderScreen"

export function CaseAssessment() {
  const { id } = useParams<{ id: string }>()

  return (
    <PlaceholderScreen
      icon={ScanSearch}
      title={`Assessment${id ? ` — ${id}` : ""}`}
      description="Case strength findings, recovery range estimates, and law citations from the assessment agent will be shown here."
    />
  )
}
