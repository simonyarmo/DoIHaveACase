import * as React from "react"
import { CheckCircle2, Loader2, Upload, XCircle } from "lucide-react"

import { cn } from "@/lib/utils"

interface FileDropzoneProps {
  label: string
  description?: string
  accept?: string
  existingFileName?: string | null
  onUpload: (file: File) => Promise<void>
  disabled?: boolean
  className?: string
}

export function FileDropzone({ label, description, accept, existingFileName, onUpload, disabled, className }: FileDropzoneProps) {
  const [status, setStatus] = React.useState<"idle" | "uploading" | "success" | "error">("idle")
  const [fileName, setFileName] = React.useState<string | null>(existingFileName ?? null)
  const [error, setError] = React.useState<string | null>(null)
  const [dragging, setDragging] = React.useState(false)
  const inputRef = React.useRef<HTMLInputElement>(null)

  React.useEffect(() => {
    if (existingFileName) {
      setFileName(existingFileName)
      setStatus("success")
    }
  }, [existingFileName])

  const handleFile = async (file: File | undefined) => {
    if (!file || disabled) return
    setStatus("uploading")
    setError(null)
    try {
      await onUpload(file)
      setFileName(file.name)
      setStatus("success")
    } catch (err) {
      setStatus("error")
      setError(err instanceof Error ? err.message : "Upload failed")
    }
  }

  return (
    <div className={cn("space-y-1", className)}>
      <div
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") inputRef.current?.click()
        }}
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragging(false)
          void handleFile(e.dataTransfer.files?.[0])
        }}
        className={cn(
          "flex cursor-pointer flex-col items-center gap-2 rounded-md border-2 border-dashed border-input p-4 text-center transition-colors hover:bg-accent",
          dragging && "border-primary bg-primary/5",
          disabled && "cursor-not-allowed opacity-50"
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          className="hidden"
          disabled={disabled}
          onChange={(e) => void handleFile(e.target.files?.[0])}
        />

        {status === "uploading" ? (
          <Loader2 className="h-5 w-5 animate-spin text-primary" />
        ) : status === "success" ? (
          <CheckCircle2 className="h-5 w-5 text-primary" />
        ) : status === "error" ? (
          <XCircle className="h-5 w-5 text-destructive" />
        ) : (
          <Upload className="h-5 w-5 text-muted-foreground" />
        )}

        <div className="text-sm font-medium">{label}</div>
        {description && <p className="text-xs text-muted-foreground">{description}</p>}

        {fileName && status !== "error" && <p className="text-xs text-primary">{fileName}</p>}
        {status === "error" && <p className="text-xs text-destructive">{error}</p>}
        {status === "idle" && !fileName && <p className="text-xs text-muted-foreground">Click or drag a file here</p>}
      </div>
    </div>
  )
}
