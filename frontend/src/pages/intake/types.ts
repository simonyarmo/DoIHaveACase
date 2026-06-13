import type { CaseDetailResponse } from "@/types/case"

export interface StepProps {
  caseId: string
  data: CaseDetailResponse
  onNext: () => void
  onBack?: () => void
  refresh: () => Promise<unknown>
}
