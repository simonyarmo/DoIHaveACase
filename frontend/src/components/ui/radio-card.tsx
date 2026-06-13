import * as React from "react"

import { cn } from "@/lib/utils"

interface RadioCardProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string
  description?: string
}

export const RadioCard = React.forwardRef<HTMLInputElement, RadioCardProps>(
  ({ className, label, description, id, ...props }, ref) => {
    return (
      <label
        htmlFor={id}
        className={cn(
          "flex cursor-pointer items-start gap-3 rounded-md border border-input p-3 text-sm transition-colors hover:bg-accent has-[:checked]:border-primary has-[:checked]:bg-primary/5",
          className
        )}
      >
        <input
          type="radio"
          id={id}
          ref={ref}
          style={{ accentColor: "hsl(var(--primary))" }}
          className="mt-0.5 h-4 w-4 border-input"
          {...props}
        />
        <span>
          <span className="font-medium">{label}</span>
          {description && <span className="block text-muted-foreground">{description}</span>}
        </span>
      </label>
    )
  }
)
RadioCard.displayName = "RadioCard"
