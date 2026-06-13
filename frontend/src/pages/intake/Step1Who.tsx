import { useEffect, useRef } from "react"
import { useForm } from "react-hook-form"
import { useMutation, useQuery } from "@tanstack/react-query"

import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { getCurrentUser, updateCase } from "@/lib/api"
import type { StepProps } from "./types"
import { StepNav } from "./StepNav"

interface FormValues {
  full_legal_name: string
  address: string
  phone: string
}

export function Step1Who({ caseId, data, onNext, refresh }: StepProps) {
  const tenant = data.parties.find((p) => p.role === "tenant")
  const { data: me, isSuccess: meLoaded } = useQuery({ queryKey: ["me"], queryFn: getCurrentUser })

  const { register, handleSubmit, setValue, getValues } = useForm<FormValues>({
    defaultValues: {
      full_legal_name: tenant?.full_legal_name ?? "",
      address: tenant?.address ?? "",
      phone: "",
    },
  })

  const phoneInitialized = useRef(false)
  useEffect(() => {
    if (!meLoaded || phoneInitialized.current) return
    phoneInitialized.current = true
    if (me?.phone_number && !getValues("phone")) {
      setValue("phone", me.phone_number)
    }
  }, [meLoaded, me, getValues, setValue])

  const mutation = useMutation({
    mutationFn: (values: FormValues) => updateCase(caseId, { tenant: values }),
    onSuccess: async () => {
      await refresh()
      onNext()
    },
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Who you are</h1>
        <p className="text-sm text-muted-foreground">We'll use this to identify you on demand letters and filings.</p>
      </div>

      <form onSubmit={handleSubmit((values) => mutation.mutate(values))} className="space-y-4">
        <div className="space-y-1">
          <Label htmlFor="full_legal_name">Full legal name</Label>
          <Input id="full_legal_name" {...register("full_legal_name", { required: true })} />
        </div>

        <div className="space-y-1">
          <Label htmlFor="address">Current address</Label>
          <Input id="address" placeholder="Street, city, state, ZIP" {...register("address", { required: true })} />
        </div>

        <div className="space-y-1">
          <Label htmlFor="email">Email</Label>
          <Input id="email" type="email" value={me?.email ?? ""} disabled readOnly />
          <p className="text-xs text-muted-foreground">This is your account email and can't be changed here.</p>
        </div>

        <div className="space-y-1">
          <Label htmlFor="phone">Phone number</Label>
          <Input id="phone" type="tel" placeholder="(555) 555-5555" {...register("phone", { required: true })} />
        </div>

        <StepNav submitting={mutation.isPending} error={mutation.isError ? "Couldn't save — please try again." : null} />
      </form>
    </div>
  )
}
