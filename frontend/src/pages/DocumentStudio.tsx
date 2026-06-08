import { useParams } from "react-router-dom"
import { FileText } from "lucide-react"

import { PlaceholderScreen } from "@/components/PlaceholderScreen"

export function DocumentStudio() {
  const { id } = useParams<{ id: string }>()

  return (
    <PlaceholderScreen
      icon={FileText}
      title={`Document studio${id ? ` — ${id}` : ""}`}
      description="Generated demand letters and petitions with inline, resolvable comments will be editable here."
    />
  )
}
