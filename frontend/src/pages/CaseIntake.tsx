import { useEffect, useRef } from "react"
import { Navigate, useNavigate, useParams } from "react-router-dom"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Check } from "lucide-react"

import { createCase, getCase } from "@/lib/api"
import { cn } from "@/lib/utils"
import { useIntakeStore } from "@/store/intakeStore"
import { Step1Who } from "@/pages/intake/Step1Who"
import { Step2Property } from "@/pages/intake/Step2Property"
import { Step3Deposit } from "@/pages/intake/Step3Deposit"
import { Step4Evidence } from "@/pages/intake/Step4Evidence"
import { Step5Review } from "@/pages/intake/Step5Review"

const STEPS = [
  { n: 1, title: "Who you are", component: Step1Who },
  { n: 2, title: "The property", component: Step2Property },
  { n: 3, title: "The deposit", component: Step3Deposit },
  { n: 4, title: "Evidence", component: Step4Evidence },
  { n: 5, title: "Review", component: Step5Review },
]

export function CaseIntake() {
  const { n } = useParams<{ n?: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const caseId = useIntakeStore((s) => s.caseId)
  const setCaseId = useIntakeStore((s) => s.setCaseId)
  const resetIntake = useIntakeStore((s) => s.reset)
  const creating = useRef(false)

  const step = n ? Number(n) : 1
  const stepIsValid = Number.isInteger(step) && step >= 1 && step <= STEPS.length

  const createCaseMutation = useMutation({ mutationFn: createCase })

  useEffect(() => {
    if (caseId || creating.current) return
    creating.current = true
    createCaseMutation.mutate(undefined, {
      onSuccess: (created) => setCaseId(created.id),
      onError: () => {
        creating.current = false
      },
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [caseId])

  const { data, isLoading, isError } = useQuery({
    queryKey: ["case", caseId],
    queryFn: () => getCase(caseId!),
    enabled: !!caseId,
  })

  if (!stepIsValid) {
    return <Navigate to="/cases/new/step/1" replace />
  }

  if (isError) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
        <p className="text-muted-foreground">We couldn't load your case. It may have been removed.</p>
        <button
          type="button"
          className="text-sm font-medium text-primary underline"
          onClick={() => {
            resetIntake()
            navigate("/cases/new/step/1")
          }}
        >
          Start a new case
        </button>
      </div>
    )
  }

  if (!caseId || isLoading || !data) {
    return <div className="flex h-full items-center justify-center text-muted-foreground">Loading…</div>
  }

  const goTo = (target: number) => navigate(`/cases/new/step/${target}`)
  const refresh = () => queryClient.invalidateQueries({ queryKey: ["case", caseId] })

  const Current = STEPS[step - 1].component

  return (
    <div className="mx-auto max-w-2xl p-8">
      <ol className="mb-8 flex items-center justify-between">
        {STEPS.map(({ n: stepNumber, title }, i) => (
          <li key={stepNumber} className="flex flex-1 items-center">
            <div className="flex flex-col items-center gap-1 text-center">
              <div
                className={cn(
                  "flex h-8 w-8 items-center justify-center rounded-full border text-sm font-medium",
                  stepNumber < step && "border-primary bg-primary text-primary-foreground",
                  stepNumber === step && "border-primary text-primary",
                  stepNumber > step && "border-border text-muted-foreground"
                )}
              >
                {stepNumber < step ? <Check className="h-4 w-4" /> : stepNumber}
              </div>
              <span className={cn("text-xs", stepNumber === step ? "font-medium text-foreground" : "text-muted-foreground")}>
                {title}
              </span>
            </div>
            {i < STEPS.length - 1 && <div className={cn("mx-2 h-px flex-1", stepNumber < step ? "bg-primary" : "bg-border")} />}
          </li>
        ))}
      </ol>

      <Current
        caseId={caseId}
        data={data}
        onNext={() => goTo(Math.min(step + 1, STEPS.length))}
        onBack={step > 1 ? () => goTo(step - 1) : undefined}
        refresh={refresh}
      />
    </div>
  )
}
