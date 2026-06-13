import { Link, useParams } from "react-router-dom"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { RefreshCw } from "lucide-react"

import { ExpenseTracker } from "@/components/ExpenseTracker"
import { Button } from "@/components/ui/button"
import { getAssessment, refreshAssessment } from "@/lib/api"
import { cn } from "@/lib/utils"
import type { CaseStrength, Defense, Finding, StrengthBars } from "@/types/case"

export const STRENGTH_LABELS: Record<CaseStrength, string> = {
  strong: "Strong case",
  moderate: "Moderate case",
  weak: "Not yet ripe",
  no_case: "No case",
}

export const STRENGTH_BADGE_STYLES: Record<CaseStrength, string> = {
  strong: "bg-green-100 text-green-800",
  moderate: "bg-amber-100 text-amber-800",
  weak: "bg-secondary text-secondary-foreground",
  no_case: "bg-secondary text-secondary-foreground",
}

const STRENGTH_BAR_LABELS: { key: keyof StrengthBars; label: string }[] = [
  { key: "violation_clear", label: "Violation clarity" },
  { key: "bad_faith_case", label: "Bad-faith indicators" },
  { key: "evidence_quality", label: "Evidence quality" },
  { key: "procedural_risk", label: "Procedural standing" },
]

const ACTION_PLAN_ORDER = ["demand_letter_required", "deadline", "filing_required", "service_required", "hearing"]

export function formatCurrency(value: number): string {
  return value.toLocaleString("en-US", { style: "currency", currency: "USD" })
}

function StrengthBarRow({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>{label}</span>
        <span>{value}%</span>
      </div>
      <div className="mt-1 h-2 rounded-full bg-muted">
        <div className="h-2 rounded-full bg-primary" style={{ width: `${value}%` }} />
      </div>
    </div>
  )
}

function FindingRow({ finding, tone }: { finding: Finding; tone: "good" | "caution" | "bad" }) {
  const dotClass = { good: "bg-green-500", caution: "bg-amber-500", bad: "bg-red-500" }[tone]

  return (
    <li className="flex gap-2 text-sm">
      <span className={cn("mt-1.5 h-2 w-2 flex-none rounded-full", dotClass)} />
      <div>
        <p>{finding.text}</p>
        {finding.explanation && <p className="text-xs text-muted-foreground">{finding.explanation}</p>}
        {finding.impact && <p className="text-xs text-muted-foreground">{finding.impact}</p>}
        {finding.statute && <p className="text-xs text-muted-foreground">{finding.statute}</p>}
      </div>
    </li>
  )
}

function DefenseCard({ defense }: { defense: Defense }) {
  return (
    <li className="space-y-1 rounded-md border border-border p-3 text-sm">
      <p className="font-medium">{defense.defense}</p>
      <p className="text-xs text-muted-foreground">
        <span className="font-medium text-foreground">Landlord must show: </span>
        {defense.landlord_burden}
      </p>
      <p className="text-xs text-muted-foreground">
        <span className="font-medium text-foreground">Your response: </span>
        {defense.tenant_response}
      </p>
    </li>
  )
}

export function CaseAssessment() {
  const { id } = useParams<{ id: string }>()
  const caseId = id ?? null
  const queryClient = useQueryClient()

  const { data } = useQuery({
    queryKey: ["assessment", caseId],
    queryFn: () => getAssessment(caseId!),
    enabled: !!caseId,
    refetchInterval: (query) => {
      const d = query.state.data
      if (!d) return false
      if (d.case.status === "researching" || d.case.status === "assessment" || d.details.case_strength == null) {
        return 3000
      }
      return false
    },
  })

  const refreshMutation = useMutation({
    mutationFn: () => refreshAssessment(caseId!),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["assessment", caseId] })
      await queryClient.invalidateQueries({ queryKey: ["case", caseId] })
    },
  })

  if (!caseId || !data) {
    return <div className="flex h-full items-center justify-center text-muted-foreground">Loading…</div>
  }

  const { case: caseInfo, details, strength_bars, timeline_events } = data

  if (caseInfo.status === "intake") {
    return (
      <div className="p-6">
        <div className="rounded-md border border-border p-4 text-sm">
          <h1 className="text-lg font-semibold">Assessment not available yet</h1>
          <p className="mt-1 text-muted-foreground">Finish and submit your case intake to get a case assessment.</p>
          <Link to={`/cases/${caseId}`} className="mt-3 inline-block text-sm font-medium text-primary hover:underline">
            Continue your case →
          </Link>
        </div>
      </div>
    )
  }

  if (caseInfo.status === "researching" || caseInfo.status === "assessment" || details.case_strength == null) {
    return (
      <div className="p-6">
        <div className="rounded-md border border-border p-4 text-sm">
          <h1 className="text-lg font-semibold">Assessment in progress</h1>
          <p className="mt-1 text-muted-foreground">
            We're evaluating your case against your state's security-deposit law. This usually takes less than a
            minute.
          </p>
          <Link to={`/cases/${caseId}`} className="mt-3 inline-block text-sm font-medium text-primary hover:underline">
            View research progress →
          </Link>
        </div>
      </div>
    )
  }

  if (details.case_strength === "no_case") {
    return (
      <div className="p-6">
        <div className="space-y-2 rounded-md border border-border p-4">
          <span className={cn("inline-block rounded-full px-2 py-1 text-xs font-medium", STRENGTH_BADGE_STYLES.no_case)}>
            {STRENGTH_LABELS.no_case}
          </span>
          <h1 className="text-lg font-semibold">{details.property_address ?? "Your case"}</h1>
          <p className="text-sm">{details.recommended_path}</p>
          {details.findings_caution && details.findings_caution.length > 0 && (
            <ul className="space-y-2 pt-2">
              {details.findings_caution.map((finding, i) => (
                <FindingRow key={i} finding={finding} tone="caution" />
              ))}
            </ul>
          )}
          <Button variant="outline" size="sm" onClick={() => refreshMutation.mutate()} disabled={refreshMutation.isPending}>
            <RefreshCw className="h-4 w-4" /> Re-run assessment
          </Button>
        </div>
      </div>
    )
  }

  const strength = details.case_strength
  const recoveryMin = details.estimated_recovery_min ?? 0
  const recoveryMax = details.estimated_recovery_max ?? 0

  const sortedEvents = [...timeline_events].sort(
    (a, b) => ACTION_PLAN_ORDER.indexOf(a.event_type) - ACTION_PLAN_ORDER.indexOf(b.event_type)
  )

  const isUnlocked = (index: number): boolean => {
    if (index === 0) return true
    const prev = sortedEvents[index - 1]
    if (prev.completed) return true
    if (prev.event_type === "deadline" && prev.event_date) {
      return new Date(prev.event_date) <= new Date()
    }
    return false
  }

  return (
    <div className="flex h-full">
      <div className="flex-1 space-y-4 overflow-y-auto p-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold">{details.property_address ?? "Your case"}</h1>
            <p className="text-sm text-muted-foreground">
              Status: <span className="font-medium text-foreground">{caseInfo.status.replace(/_/g, " ")}</span>
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={() => refreshMutation.mutate()} disabled={refreshMutation.isPending}>
            <RefreshCw className="h-4 w-4" /> Re-run assessment
          </Button>
        </div>

        <div className="space-y-4 rounded-md border border-border p-4">
          <span className={cn("inline-block rounded-full px-2 py-1 text-xs font-medium", STRENGTH_BADGE_STYLES[strength])}>
            {STRENGTH_LABELS[strength]}
          </span>
          <div>
            <h2 className="text-2xl font-semibold">
              {formatCurrency(recoveryMin)} – {formatCurrency(recoveryMax)}
            </h2>
            <p className="text-sm text-muted-foreground">Estimated recovery range</p>
          </div>
          {details.recommended_path && <p className="text-sm">{details.recommended_path}</p>}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {STRENGTH_BAR_LABELS.map(({ key, label }) => (
              <StrengthBarRow key={key} label={label} value={strength_bars[key]} />
            ))}
          </div>
        </div>

        {details.findings_good && details.findings_good.length > 0 && (
          <div className="space-y-2 rounded-md border border-border p-4">
            <h2 className="font-medium">What's working in your favor</h2>
            <ul className="space-y-2">
              {details.findings_good.map((f, i) => (
                <FindingRow key={i} finding={f} tone="good" />
              ))}
            </ul>
          </div>
        )}

        {details.findings_caution && details.findings_caution.length > 0 && (
          <div className="space-y-2 rounded-md border border-border p-4">
            <h2 className="font-medium">Worth keeping in mind</h2>
            <ul className="space-y-2">
              {details.findings_caution.map((f, i) => (
                <FindingRow key={i} finding={f} tone="caution" />
              ))}
            </ul>
          </div>
        )}

        {details.findings_bad && details.findings_bad.length > 0 && (
          <div className="space-y-2 rounded-md border border-border p-4">
            <h2 className="font-medium">Issues with your landlord's position</h2>
            <ul className="space-y-2">
              {details.findings_bad.map((f, i) => (
                <FindingRow key={i} finding={f} tone="bad" />
              ))}
            </ul>
          </div>
        )}

        {details.defenses_likely && details.defenses_likely.length > 0 && (
          <div className="space-y-2 rounded-md border border-border p-4">
            <h2 className="font-medium">Defenses your landlord may raise</h2>
            <ul className="space-y-2">
              {details.defenses_likely.map((d, i) => (
                <DefenseCard key={i} defense={d} />
              ))}
            </ul>
          </div>
        )}

        {details.exceeds_jurisdiction && details.jurisdiction_options && (
          <div className="space-y-2 rounded-md border border-border p-4">
            <h2 className="font-medium">Filing court options</h2>
            <ul className="list-inside list-disc space-y-1 text-sm">
              {details.jurisdiction_options.map((opt, i) => (
                <li key={i}>{opt}</li>
              ))}
            </ul>
          </div>
        )}

        {sortedEvents.length > 0 && (
          <div className="space-y-2 rounded-md border border-border p-4">
            <h2 className="font-medium">Action plan</h2>
            <ol className="space-y-3">
              {sortedEvents.map((event, i) => {
                const unlocked = isUnlocked(i)
                return (
                  <li key={event.id} className={cn("rounded-md border border-border p-3 text-sm", !unlocked && "opacity-50")}>
                    <div className="flex items-center justify-between">
                      <p className="font-medium">{event.title}</p>
                      {event.completed && <span className="text-xs text-green-700">Done</span>}
                    </div>
                    {event.description && <p className="mt-1 text-muted-foreground">{event.description}</p>}
                    {event.event_date && <p className="mt-1 text-xs text-muted-foreground">Due: {event.event_date}</p>}
                  </li>
                )
              })}
            </ol>
          </div>
        )}
      </div>

      <div className="w-96 overflow-y-auto border-l border-border p-4">
        <ExpenseTracker caseId={caseId} />
      </div>
    </div>
  )
}
