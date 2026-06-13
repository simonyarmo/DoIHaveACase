import { useNavigate } from "react-router-dom"
import { useMutation } from "@tanstack/react-query"
import { Pencil } from "lucide-react"

import { Button } from "@/components/ui/button"
import { ApiError, submitCase } from "@/lib/api"
import { COMMUNICATION_OPTIONS, EVIDENCE_UPLOADS, LANDLORD_TYPE_OPTIONS, US_STATES } from "@/lib/constants"
import { useIntakeStore } from "@/store/intakeStore"
import type { StepProps } from "./types"

function Row({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div className="flex justify-between gap-4 py-1 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="text-right font-medium">{value || "—"}</span>
    </div>
  )
}

function Section({ title, step, children }: { title: string; step: number; children: React.ReactNode }) {
  const navigate = useNavigate()
  return (
    <div className="space-y-1 rounded-md border border-border p-4">
      <div className="flex items-center justify-between">
        <h2 className="font-medium">{title}</h2>
        <Button type="button" variant="ghost" size="sm" onClick={() => navigate(`/cases/new/step/${step}`)}>
          <Pencil className="mr-1 h-3.5 w-3.5" />
          Edit
        </Button>
      </div>
      {children}
    </div>
  )
}

export function Step5Review({ caseId, data, onBack }: StepProps) {
  const navigate = useNavigate()
  const reset = useIntakeStore((s) => s.reset)
  const { details, parties, documents } = data
  const tenant = parties.find((p) => p.role === "tenant")
  const stateName = US_STATES.find((s) => s.code === details.property_state)?.name ?? details.property_state
  const landlordTypeLabel = LANDLORD_TYPE_OPTIONS.find((o) => o.value === details.landlord_type)?.label
  const communicationLabel = COMMUNICATION_OPTIONS.find((o) => o.value === details.landlord_communication)?.label

  const mutation = useMutation({
    mutationFn: () => submitCase(caseId),
    onSuccess: () => {
      reset()
      navigate(`/cases/${caseId}`)
    },
  })

  let errorMessage: string | null = null
  if (mutation.isError) {
    const err = mutation.error
    if (err instanceof ApiError && err.status === 422 && typeof err.detail === "object" && err.detail !== null) {
      const detail = err.detail as { message?: string; missing_fields?: string[] }
      errorMessage = [detail.message, detail.missing_fields?.join(", ")].filter(Boolean).join(": ")
    } else if (err instanceof ApiError) {
      errorMessage = String(err.detail)
    } else {
      errorMessage = "Couldn't start research — please try again."
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Review</h1>
        <p className="text-sm text-muted-foreground">Check everything below, then start your case research.</p>
      </div>

      <div className="space-y-4">
        <Section title="Who you are" step={1}>
          <Row label="Full legal name" value={tenant?.full_legal_name} />
          <Row label="Current address" value={tenant?.address} />
        </Section>

        <Section title="The property" step={2}>
          <Row label="Property address" value={details.property_address} />
          <Row label="State" value={stateName} />
          <Row label="County" value={details.property_county} />
          <Row label="Landlord type" value={landlordTypeLabel} />
          <Row label="Landlord name" value={details.landlord_name_as_entered} />
          <Row label="Landlord mailing address" value={details.landlord_address} />
          <Row label="Lease uploaded" value={documents.find((d) => d.type === "lease")?.file_name ?? "Not provided"} />
        </Section>

        <Section title="The deposit" step={3}>
          <Row label="Deposit amount" value={details.deposit_amount != null ? `$${details.deposit_amount}` : null} />
          <Row label="Move-in date" value={details.move_in_date} />
          <Row label="Move-out date" value={details.move_out_date} />
          <Row label="Keys returned" value={details.keys_returned_date} />
          <Row label="Amount returned so far" value={details.amount_returned != null ? `$${details.amount_returned}` : null} />
          <Row label="Forwarding address" value={details.forwarding_address} />
          <Row label="Proof of forwarding address" value={details.forwarding_address_proof ? "Yes" : "No"} />
          <Row label="Landlord communication" value={communicationLabel} />
        </Section>

        <Section title="Evidence" step={4}>
          {EVIDENCE_UPLOADS.map((item) => (
            <Row key={item.type} label={item.label} value={documents.find((d) => d.type === item.type)?.file_name ?? "Not provided"} />
          ))}
        </Section>
      </div>

      <div className="space-y-3 pt-2">
        {errorMessage && <p className="text-sm text-destructive">{errorMessage}</p>}
        <div className="flex items-center justify-between">
          {onBack ? (
            <Button type="button" variant="outline" onClick={onBack} disabled={mutation.isPending}>
              Back
            </Button>
          ) : (
            <span />
          )}
          <Button type="button" disabled={mutation.isPending} onClick={() => mutation.mutate()}>
            {mutation.isPending ? "Starting…" : "Start research"}
          </Button>
        </div>
      </div>
    </div>
  )
}
