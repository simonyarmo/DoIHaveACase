import { Button } from "@/components/ui/button"

interface StepNavProps {
  onBack?: () => void
  nextLabel?: string
  submitting?: boolean
  error?: string | null
}

export function StepNav({ onBack, nextLabel = "Next", submitting, error }: StepNavProps) {
  return (
    <div className="space-y-3 pt-2">
      {error && <p className="text-sm text-destructive">{error}</p>}
      <div className="flex items-center justify-between">
        {onBack ? (
          <Button type="button" variant="outline" onClick={onBack} disabled={submitting}>
            Back
          </Button>
        ) : (
          <span />
        )}
        <Button type="submit" disabled={submitting}>
          {submitting ? "Saving…" : nextLabel}
        </Button>
      </div>
    </div>
  )
}
