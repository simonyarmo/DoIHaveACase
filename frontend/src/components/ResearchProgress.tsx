import { CheckCircle2, CircleDashed, Loader2, XCircle } from "lucide-react"

import { RESEARCH_STEPS } from "@/lib/constants"
import { cn } from "@/lib/utils"
import type { ProgressEvent } from "@/types/case"

interface ResearchProgressProps {
  progress: Record<string, ProgressEvent | undefined>
  hasLease: boolean
}

export function ResearchProgress({ progress, hasLease }: ResearchProgressProps) {
  const steps = RESEARCH_STEPS.filter((step) => step.tool !== "lease_parser" || hasLease)

  return (
    <div className="space-y-3 rounded-md border border-border p-4">
      <h2 className="font-medium">Research in progress</h2>
      <ul className="space-y-2">
        {steps.map((step) => {
          const event = progress[step.tool]
          const status = event?.status ?? "pending"

          return (
            <li key={step.tool} className="flex items-start gap-2 text-sm">
              {status === "complete" && <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-primary" />}
              {status === "running" && <Loader2 className="mt-0.5 h-4 w-4 shrink-0 animate-spin text-primary" />}
              {status === "error" && <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />}
              {status === "pending" && <CircleDashed className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />}
              <div>
                <p className={cn(status === "pending" && "text-muted-foreground")}>{step.label}</p>
                {status === "error" && event?.error && <p className="text-xs text-destructive">{event.error}</p>}
              </div>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
