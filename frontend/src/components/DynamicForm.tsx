import { useState } from "react"
import { useForm } from "react-hook-form"

import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import type { DynamicFormSchema } from "@/types/case"

interface DynamicFormProps {
  schema: DynamicFormSchema
  onSubmit: (values: Record<string, unknown>) => void
}

export function DynamicForm({ schema, onSubmit }: DynamicFormProps) {
  const { register, handleSubmit } = useForm<Record<string, unknown>>()
  const [submitted, setSubmitted] = useState(false)

  if (submitted) {
    return <p className="text-sm text-muted-foreground">Submitted — thanks!</p>
  }

  return (
    <form
      onSubmit={handleSubmit((values) => {
        onSubmit(values)
        setSubmitted(true)
      })}
      className="space-y-3 rounded-md border border-border bg-background p-3"
    >
      {schema.title && <p className="text-sm font-medium">{schema.title}</p>}
      {schema.fields.map((field) => (
        <div key={field.name} className="space-y-1">
          {field.type !== "checkbox" && <Label htmlFor={field.name}>{field.label}</Label>}

          {field.type === "select" ? (
            <Select id={field.name} {...register(field.name, { required: field.required })}>
              <option value="">Select…</option>
              {(field.options ?? []).map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </Select>
          ) : field.type === "textarea" ? (
            <Textarea id={field.name} {...register(field.name, { required: field.required })} />
          ) : field.type === "checkbox" ? (
            <label className="flex items-center gap-2 text-sm">
              <Checkbox {...register(field.name)} />
              {field.label}
            </label>
          ) : (
            <Input
              id={field.name}
              type={field.type === "number" ? "number" : field.type === "date" ? "date" : "text"}
              {...register(field.name, { required: field.required })}
            />
          )}
        </div>
      ))}
      <Button type="submit" size="sm">
        Submit
      </Button>
    </form>
  )
}
