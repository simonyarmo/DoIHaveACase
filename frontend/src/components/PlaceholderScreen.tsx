import type { LucideIcon } from "lucide-react"

interface PlaceholderScreenProps {
  icon: LucideIcon
  title: string
  description: string
}

export function PlaceholderScreen({ icon: Icon, title, description }: PlaceholderScreenProps) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 p-12 text-center">
      <div className="rounded-full bg-primary/10 p-4">
        <Icon className="h-8 w-8 text-primary" />
      </div>
      <h1 className="text-2xl font-semibold">{title}</h1>
      <p className="max-w-md text-muted-foreground">{description}</p>
      <p className="text-xs uppercase tracking-wide text-muted-foreground/60">Coming in a later phase</p>
    </div>
  )
}
