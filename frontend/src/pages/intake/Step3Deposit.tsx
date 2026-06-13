import { useForm } from "react-hook-form"
import { useMutation } from "@tanstack/react-query"

import { Checkbox } from "@/components/ui/checkbox"
import { FileDropzone } from "@/components/ui/file-dropzone"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { RadioCard } from "@/components/ui/radio-card"
import { COMMUNICATION_OPTIONS } from "@/lib/constants"
import { updateCase, uploadDocument } from "@/lib/api"
import type { CaseDetailsUpdate } from "@/types/case"
import type { StepProps } from "./types"
import { StepNav } from "./StepNav"

interface FormValues {
  deposit_amount: string
  move_in_date: string
  move_out_date: string
  keys_returned_date: string
  amount_returned: string
  date_returned: string
  forwarding_address: string
  forwarding_address_proof: boolean
  landlord_communication: string
}

export function Step3Deposit({ caseId, data, onNext, onBack, refresh }: StepProps) {
  const { details, documents } = data
  const forwardingProofDoc = documents.find((d) => d.type === "forwarding_proof")

  const { register, handleSubmit, watch, formState } = useForm<FormValues>({
    defaultValues: {
      deposit_amount: details.deposit_amount?.toString() ?? "",
      move_in_date: details.move_in_date ?? "",
      move_out_date: details.move_out_date ?? "",
      keys_returned_date: details.keys_returned_date ?? "",
      amount_returned: details.amount_returned?.toString() ?? "",
      date_returned: details.date_returned ?? "",
      forwarding_address: details.forwarding_address ?? "",
      forwarding_address_proof: details.forwarding_address_proof ?? false,
      landlord_communication: details.landlord_communication ?? "none",
    },
  })

  const hasProof = watch("forwarding_address_proof")

  const mutation = useMutation({
    mutationFn: (values: FormValues) => {
      const payload: CaseDetailsUpdate = {
        deposit_amount: values.deposit_amount ? Number(values.deposit_amount) : null,
        move_in_date: values.move_in_date || null,
        move_out_date: values.move_out_date || null,
        keys_returned_date: values.keys_returned_date || null,
        amount_returned: values.amount_returned ? Number(values.amount_returned) : null,
        date_returned: values.date_returned || null,
        forwarding_address: values.forwarding_address || null,
        forwarding_address_proof: values.forwarding_address_proof,
        landlord_communication: values.landlord_communication,
      }
      return updateCase(caseId, { details: payload })
    },
    onSuccess: onNext,
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">The deposit</h1>
        <p className="text-sm text-muted-foreground">Details about your security deposit and move-out.</p>
      </div>

      <form onSubmit={handleSubmit((values) => mutation.mutate(values))} className="space-y-4">
        <div className="space-y-1">
          <Label htmlFor="deposit_amount">Deposit amount</Label>
          <Input id="deposit_amount" type="number" step="0.01" min="0" placeholder="0.00" {...register("deposit_amount", { required: true })} />
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div className="space-y-1">
            <Label htmlFor="move_in_date">Move-in date</Label>
            <Input id="move_in_date" type="date" {...register("move_in_date")} />
          </div>
          <div className="space-y-1">
            <Label htmlFor="move_out_date">Move-out date</Label>
            <Input id="move_out_date" type="date" {...register("move_out_date", { required: true })} />
          </div>
          <div className="space-y-1">
            <Label htmlFor="keys_returned_date">Keys returned</Label>
            <Input id="keys_returned_date" type="date" {...register("keys_returned_date")} />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1">
            <Label htmlFor="amount_returned">Amount returned so far (if any)</Label>
            <Input id="amount_returned" type="number" step="0.01" min="0" placeholder="0.00" {...register("amount_returned")} />
          </div>
          <div className="space-y-1">
            <Label htmlFor="date_returned">Date returned</Label>
            <Input id="date_returned" type="date" {...register("date_returned")} />
          </div>
        </div>

        <div className="space-y-1">
          <Label htmlFor="forwarding_address">Forwarding address given to landlord</Label>
          <Input id="forwarding_address" placeholder="Street, city, state, ZIP" {...register("forwarding_address")} />
        </div>

        <div className="space-y-2">
          <label className="flex items-center gap-2 text-sm">
            <Checkbox {...register("forwarding_address_proof")} />
            I have proof I gave my landlord this forwarding address
          </label>
          {hasProof && (
            <FileDropzone
              label="Upload proof of forwarding address"
              description="A copy of the letter, email, or form you used."
              existingFileName={forwardingProofDoc?.file_name}
              onUpload={async (file) => {
                await uploadDocument(caseId, file, "forwarding_proof")
                await refresh()
              }}
            />
          )}
        </div>

        <div className="space-y-2">
          <Label>What has your landlord told you about the deposit?</Label>
          <div className="space-y-2">
            {COMMUNICATION_OPTIONS.map((opt) => (
              <RadioCard
                key={opt.value}
                id={`landlord_communication_${opt.value}`}
                label={opt.label}
                value={opt.value}
                {...register("landlord_communication", { required: true })}
              />
            ))}
          </div>
        </div>

        <StepNav
          onBack={onBack}
          submitting={mutation.isPending || formState.isSubmitting}
          error={mutation.isError ? "Couldn't save — please try again." : null}
        />
      </form>
    </div>
  )
}
