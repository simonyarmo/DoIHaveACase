import { FileDropzone } from "@/components/ui/file-dropzone"
import { EVIDENCE_UPLOADS } from "@/lib/constants"
import { uploadDocument } from "@/lib/api"
import { cn } from "@/lib/utils"
import type { StepProps } from "./types"
import { StepNav } from "./StepNav"

const IMPORTANCE_STYLES: Record<string, string> = {
  Required: "bg-destructive/10 text-destructive",
  "Strongly recommended": "bg-primary/10 text-primary",
  "If applicable": "bg-muted text-muted-foreground",
}

export function Step4Evidence({ caseId, data, onNext, onBack, refresh }: StepProps) {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Evidence</h1>
        <p className="text-sm text-muted-foreground">
          Upload anything you have. You can come back and add more later from the Documents tab.
        </p>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault()
          onNext()
        }}
        className="space-y-4"
      >
        {EVIDENCE_UPLOADS.map((item) => {
          const existing = data.documents.find((d) => d.type === item.type)
          return (
            <div key={item.type} className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">{item.label}</span>
                <span className={cn("rounded-full px-2 py-0.5 text-xs font-medium", IMPORTANCE_STYLES[item.importance])}>
                  {item.importance}
                </span>
              </div>
              <FileDropzone
                label={`Upload ${item.label.toLowerCase()}`}
                description={item.description}
                existingFileName={existing?.file_name}
                onUpload={async (file) => {
                  await uploadDocument(caseId, file, item.type)
                  await refresh()
                }}
              />
            </div>
          )
        })}

        <StepNav onBack={onBack} />
      </form>
    </div>
  )
}
