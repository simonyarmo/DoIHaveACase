import { useForm } from "react-hook-form"
import { useMutation } from "@tanstack/react-query"
import { Info } from "lucide-react"

import { FileDropzone } from "@/components/ui/file-dropzone"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { RadioCard } from "@/components/ui/radio-card"
import { Select } from "@/components/ui/select"
import { LANDLORD_TYPE_OPTIONS, US_STATES } from "@/lib/constants"
import { updateCase, uploadDocument } from "@/lib/api"
import type { StepProps } from "./types"
import { StepNav } from "./StepNav"

interface FormValues {
  property_address: string
  property_state: string
  property_county: string
  landlord_type: string
  landlord_name_as_entered: string
  landlord_address: string
}

export function Step2Property({ caseId, data, onNext, onBack, refresh }: StepProps) {
  const { details, documents } = data
  const leaseDocument = documents.find((d) => d.type === "lease")

  const { register, handleSubmit, formState } = useForm<FormValues>({
    defaultValues: {
      property_address: details.property_address ?? "",
      property_state: details.property_state ?? "",
      property_county: details.property_county ?? "",
      landlord_type: details.landlord_type ?? "",
      landlord_name_as_entered: details.landlord_name_as_entered ?? "",
      landlord_address: details.landlord_address ?? "",
    },
  })

  const mutation = useMutation({
    mutationFn: (values: FormValues) =>
      updateCase(caseId, {
        state: values.property_state,
        county: values.property_county || null,
        details: values,
      }),
    onSuccess: onNext,
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">The property</h1>
        <p className="text-sm text-muted-foreground">Tell us about the rental and your landlord.</p>
      </div>

      <form onSubmit={handleSubmit((values) => mutation.mutate(values))} className="space-y-4">
        <div className="space-y-1">
          <Label htmlFor="property_address">Property address</Label>
          <Input id="property_address" placeholder="Street, city, state, ZIP" {...register("property_address", { required: true })} />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1">
            <Label htmlFor="property_state">State</Label>
            <Select id="property_state" {...register("property_state", { required: true })}>
              <option value="">Select a state</option>
              {US_STATES.map((s) => (
                <option key={s.code} value={s.code}>
                  {s.name}
                </option>
              ))}
            </Select>
          </div>
          <div className="space-y-1">
            <Label htmlFor="property_county">County</Label>
            <Input id="property_county" placeholder="e.g. Harris" {...register("property_county")} />
          </div>
        </div>

        <div className="space-y-2">
          <Label>What kind of landlord do you have?</Label>
          <div className="space-y-2">
            {LANDLORD_TYPE_OPTIONS.map((opt) => (
              <RadioCard
                key={opt.value}
                id={`landlord_type_${opt.value}`}
                label={opt.label}
                value={opt.value}
                {...register("landlord_type", { required: true })}
              />
            ))}
          </div>
        </div>

        <div className="space-y-1">
          <div className="flex items-center gap-1.5">
            <Label htmlFor="landlord_name_as_entered">Landlord name (as written on your lease)</Label>
            <span title="Enter the name exactly as it appears on your lease — we'll use it to verify the business registration.">
              <Info className="h-3.5 w-3.5 text-muted-foreground" />
            </span>
          </div>
          <Input id="landlord_name_as_entered" {...register("landlord_name_as_entered", { required: true })} />
        </div>

        <div className="space-y-1">
          <Label htmlFor="landlord_address">Landlord mailing address</Label>
          <Input id="landlord_address" placeholder="Where you'd mail a demand letter" {...register("landlord_address")} />
        </div>

        <div className="space-y-1">
          <Label>Lease (optional)</Label>
          <FileDropzone
            label="Upload your lease"
            description="Optional — we'll parse it in the background while you continue."
            accept=".pdf,.docx"
            existingFileName={leaseDocument?.file_name}
            onUpload={async (file) => {
              await uploadDocument(caseId, file, "lease")
              await refresh()
            }}
          />
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
