import { Link } from "react-router-dom"
import { useQueries, useQuery } from "@tanstack/react-query"
import { FilePlus2 } from "lucide-react"

import { listCases, listExpenses } from "@/lib/api"
import { cn } from "@/lib/utils"
import { formatCurrency, STRENGTH_BADGE_STYLES, STRENGTH_LABELS } from "@/pages/CaseAssessment"
import type { CaseSummary } from "@/types/case"

function CaseCard({ case: c }: { case: CaseSummary }) {
  return (
    <Link to={`/cases/${c.id}`} className="block space-y-1 rounded-md border border-border p-4 transition-colors hover:bg-accent">
      <div className="flex items-center justify-between gap-2">
        <h2 className="font-medium">{c.property_address ?? "Untitled case"}</h2>
        {c.case_strength && (
          <span className={cn("flex-none rounded-full px-2 py-1 text-xs font-medium", STRENGTH_BADGE_STYLES[c.case_strength])}>
            {STRENGTH_LABELS[c.case_strength]}
          </span>
        )}
      </div>
      <p className="text-sm text-muted-foreground">
        Status: <span className="font-medium text-foreground">{c.status.replace(/_/g, " ")}</span>
        {(c.county || c.state) && ` · ${[c.county, c.state].filter(Boolean).join(", ")}`}
      </p>
      {c.estimated_recovery_min != null && c.estimated_recovery_max != null && (
        <p className="text-sm">
          Estimated recovery: {formatCurrency(c.estimated_recovery_min)} – {formatCurrency(c.estimated_recovery_max)}
        </p>
      )}
    </Link>
  )
}

export function Dashboard() {
  const { data: cases } = useQuery({ queryKey: ["cases"], queryFn: listCases })

  const expenseQueries = useQueries({
    queries: (cases ?? []).map((c) => ({
      queryKey: ["expenses", c.id],
      queryFn: () => listExpenses(c.id),
    })),
  })

  const totalRecoverable = expenseQueries.reduce(
    (sum, q) => sum + (q.data ?? []).filter((e) => e.recoverable).reduce((s, e) => s + e.amount, 0),
    0
  )

  return (
    <div className="space-y-4 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Dashboard</h1>
        <Link
          to="/cases/new"
          className="inline-flex h-9 items-center gap-2 rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
        >
          <FilePlus2 className="h-4 w-4" /> New case
        </Link>
      </div>

      <div className="rounded-md border border-border p-4">
        <p className="text-sm text-muted-foreground">Total recoverable expenses across all cases</p>
        <p className="text-2xl font-semibold">{formatCurrency(totalRecoverable)}</p>
      </div>

      {cases && cases.length === 0 && (
        <div className="rounded-md border border-border p-4 text-sm text-muted-foreground">
          You don't have any cases yet.{" "}
          <Link to="/cases/new" className="font-medium text-primary hover:underline">
            Start a new case
          </Link>
          .
        </div>
      )}

      <div className="space-y-3">
        {cases?.map((c) => (
          <CaseCard key={c.id} case={c} />
        ))}
      </div>
    </div>
  )
}
